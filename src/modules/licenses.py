import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. GIAO DIỆN CHUẨN APPLE (UI/UX) ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .stMetric { background: #f5f5f7; padding: 15px; border-radius: 12px; border: 1px solid #d2d2d7; }
        [data-testid="stExpander"] { border-radius: 12px; border: 1px solid #d2d2d7; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU ---
    res = supabase.table("licenses").select("*").execute()
    df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. TIÊU ĐỀ & XUẤT BÁO CÁO ---
    c_header, c_export = st.columns([3, 1])
    with c_header:
        st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)
    with c_export:
        if not df_raw.empty:
            # Xuất Excel (Sử dụng utf-16 để tránh lỗi font Tiếng Việt)
            csv = df_raw.to_csv(index=False).encode('utf-16')
            st.download_button("📥 Xuất báo cáo Excel", data=csv, 
                             file_name=f"Bao_cao_Ban_quyen_{date.today()}.csv", 
                             mime='text/csv', use_container_width=True)

    if not df_raw.empty:
        # --- 4. XỬ LÝ DỮ LIỆU AN TOÀN (FIX LỖI .dt) ---
        df = df_raw.copy()
        df['total_quantity'] = pd.to_numeric(df['total_quantity'], errors='coerce').fillna(0).astype(int)
        df['used_quantity'] = pd.to_numeric(df['used_quantity'], errors='coerce').fillna(0).astype(int)
        df['remaining'] = df['total_quantity'] - df['used_quantity']
        
        # Chuyển đổi ngày tháng an toàn
        df['expiry_date_dt'] = pd.to_datetime(df['expiry_date'], errors='coerce')
        today = pd.Timestamp(date.today())
        
        # Tính toán rủi ro: Cần xử lý khi Hết bản quyền HOẶC sắp hết hạn (< 30 ngày)
        df['days_diff'] = (df['expiry_date_dt'] - today).dt.days
        issues_df = df[(df['remaining'] <= 0) | (df['days_diff'] <= 30)]
        num_issues = len(issues_df)

        # --- 5. HIỂN THỊ KPI (4 CHỈ SỐ VÀNG) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng phần mềm", len(df))
        col2.metric("Tổng bản quyền", df['total_quantity'].sum())
        col3.metric("⚠️ Cần xử lý", num_issues, delta=f"{num_issues} rủi ro", delta_color="inverse")
        usage_rate = (df['used_quantity'].sum() / df['total_quantity'].sum() * 100) if df['total_quantity'].sum() > 0 else 0
        col4.metric("Tỷ lệ sử dụng", f"{usage_rate:.1f}%")

        # --- 6. DANH SÁCH CHI TIẾT (VIỆT HÓA 100%) ---
        st.markdown("### 📋 Danh sách bản quyền chi tiết")
        st.dataframe(
            df[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("🏷️ Tên phần mềm"),
                "total_quantity": st.column_config.NumberColumn("🔢 Tổng số"),
                "used_quantity": st.column_config.NumberColumn("📤 Đã gán"),
                "remaining": st.column_config.ProgressColumn(
                    "🟢 Khả dụng", 
                    min_value=0, 
                    max_value=int(df['total_quantity'].max()) if len(df) > 0 else 100,
                    format="%d"
                ),
                "expiry_date": st.column_config.DateColumn("📅 Ngày hết hạn")
            }
        )

        st.markdown("---")

        # --- 7. CHỨC NĂNG THU HỒI (HARVESTING) ---
        with st.expander("🔄 THU HỒI BẢN QUYỀN (Từ máy hỏng / Nhân viên nghỉ)"):
            st.info("Hệ thống sẽ cộng lại License vào kho sau khi thu hồi từ thiết bị.")
            res_assets = supabase.table("assets").select("id, asset_tag, software_list").execute()
            # Lọc các máy có cài phần mềm
            assets_with_sw = [a for a in res_assets.data if a.get('software_list') and len(a['software_list']) > 0]
            
            if assets_with_sw:
                with st.form("form_harvest"):
                    selected_asset = st.selectbox("Chọn thiết bị nguồn", assets_with_sw, 
                                                format_func=lambda x: f"{x['asset_tag']} (Có {len(x['software_list'])} phần mềm)")
                    sw_to_remove = st.multiselect("Chọn các phần mềm cần thu hồi", selected_asset['software_list'])
                    
                    if st.form_submit_button("Xác nhận thu hồi ngay", type="primary"):
                        if sw_to_remove:
                            # 1. Cập nhật bảng Assets
                            new_sw_list = [s for s in selected_asset['software_list'] if s not in sw_to_remove]
                            supabase.table("assets").update({"software_list": new_sw_list}).eq("id", selected_asset['id']).execute()
                            
                            # 2. Cập nhật bảng Licenses (Cộng lại số lượng)
                            for sw in sw_to_remove:
                                lic_res = supabase.table("licenses").select("id, used_quantity").eq("name", sw).execute()
                                if lic_res.data:
                                    old_used = lic_res.data[0]['used_quantity'] or 0
                                    supabase.table("licenses").update({"used_quantity": max(0, old_used - 1)}).eq("id", lic_res.data[0]['id']).execute()
                            
                            st.success(f"Đã thu hồi {len(sw_to_remove)} bản quyền thành công!")
                            st.rerun()
            else:
                st.write("Hiện không có thiết bị nào đang gán bản quyền.")

    # --- 8. THÊM / CẬP NHẬT ---
    with st.expander("＋ Thêm hoặc Cập nhật phần mềm"):
        with st.form("form_add_sw"):
            c1, c2 = st.columns(2)
            name_in = c1.text_input("Tên phần mềm (Đúng tên để cập nhật)")
            qty_in = c2.number_input("Tổng số lượng sở hữu", min_value=0, step=1)
            expiry_in = st.date_input("Ngày hết hạn bản quyền", value=date.today())
            
            if st.form_submit_button("Lưu vào hệ thống"):
                if name_in:
                    supabase.table("licenses").upsert({
                        "name": name_in.strip(),
                        "total_quantity": qty_in,
                        "expiry_date": str(expiry_in)
                    }, on_conflict="name").execute()
                    st.success(f"Đã cập nhật dữ liệu cho {name_in}")
                    st.rerun()

    # --- 9. GỠ BỎ ---
    if not df_raw.empty:
        with st.expander("🗑️ Gỡ bỏ phần mềm khỏi hệ thống"):
            del_target = st.selectbox("Chọn tên phần mềm cần xóa vĩnh viễn", ["-- Chọn --"] + df['name'].tolist())
            if st.button("Xác nhận xóa", type="secondary"):
                if del_target != "-- Chọn --":
                    supabase.table("licenses").delete().eq("name", del_target).execute()
                    st.success(f"Đã xóa {del_target}")
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu bản quyền. Vui lòng thêm phần mềm đầu tiên.")
