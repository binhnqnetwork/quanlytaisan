import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. GIAO DIỆN CHUẨN APPLE (UI/UX) ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .stMetric { background: white; padding: 20px; border-radius: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e5e5e7; }
        [data-testid="stExpander"] { border-radius: 12px; border: 1px solid #d2d2d7; background: white; }
        .status-critical { color: #ff3b30; font-weight: bold; }
        .status-warning { color: #ff9500; font-weight: bold; }
        .status-normal { color: #34c759; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU TẬP TRUNG ---
    # Sử dụng spinner để trải nghiệm mượt mà hơn
    with st.spinner("Đang đồng bộ kho bản quyền..."):
        res = supabase.table("licenses").select("*").order("name").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. TIÊU ĐỀ & XUẤT BÁO CÁO ---
    c_header, c_export = st.columns([3, 1])
    with c_header:
        st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)
    
    if not df_raw.empty:
        with c_export:
            # Chuyển Excel chuẩn UTF-8-SIG để Excel đọc được Tiếng Việt ngay lập tức
            csv = df_raw.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Xuất báo cáo (Excel)", data=csv, 
                             file_name=f"License_Report_{date.today()}.csv", 
                             mime='text/csv', use_container_width=True)

        # --- 4. XỬ LÝ DỮ LIỆU & PHÂN TÍCH RỦI RO ---
        df = df_raw.copy()
        df['total_quantity'] = pd.to_numeric(df['total_quantity'], errors='coerce').fillna(0).astype(int)
        df['used_quantity'] = pd.to_numeric(df['used_quantity'], errors='coerce').fillna(0).astype(int)
        df['remaining'] = df['total_quantity'] - df['used_quantity']
        df['expiry_date_dt'] = pd.to_datetime(df['expiry_date'], errors='coerce')
        
        today = pd.Timestamp(date.today())
        df['days_diff'] = (df['expiry_date_dt'] - today).dt.days
        
        # Phân loại rủi ro
        critical_df = df[(df['remaining'] < 0) | (df['days_diff'] <= 7)]
        warning_df = df[(df['remaining'] == 0) | ((df['days_diff'] > 7) & (df['days_diff'] <= 30))]
        num_issues = len(critical_df) + len(warning_df)

        # --- 5. HIỂN THỊ KPI (4 CHỈ SỐ VÀNG) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng phần mềm", len(df))
        col2.metric("Tổng bản quyền", df['total_quantity'].sum())
        
        # Chỉ số rủi ro có màu sắc cảnh báo
        col3.metric("⚠️ Rủi ro/Hết hạn", num_issues, 
                    delta=f"{len(critical_df)} Nghiêm trọng" if len(critical_df) > 0 else None,
                    delta_color="inverse")
        
        usage_rate = (df['used_quantity'].sum() / df['total_quantity'].sum() * 100) if df['total_quantity'].sum() > 0 else 0
        col4.metric("Tỷ lệ lấp đầy", f"{usage_rate:.1f}%")

        # --- 6. DANH SÁCH CHI TIẾT (SMART TABLE) ---
        st.markdown("### 📋 Trạng thái kho License")
        
        # Tạo cột trạng thái để người dùng dễ nhìn
        def get_status(row):
            if row['days_diff'] < 0: return "❌ Đã hết hạn"
            if row['days_diff'] <= 30: return "⚠️ Sắp hết hạn"
            if row['remaining'] < 0: return "❗ Dùng quá số lượng"
            return "✅ Ổn định"

        df['Trạng thái'] = df.apply(get_status, axis=1)

        st.data_editor(
            df[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date', 'Trạng thái']],
            use_container_width=True,
            hide_index=True,
            disabled=True, # Ngăn sửa trực tiếp trên bảng này
            column_config={
                "name": st.column_config.TextColumn("🏷️ Tên phần mềm", width="medium"),
                "total_quantity": st.column_config.NumberColumn("🔢 Tổng"),
                "used_quantity": st.column_config.NumberColumn("📤 Đã cấp"),
                "remaining": st.column_config.ProgressColumn(
                    "🟢 Khả dụng", 
                    min_value=0, 
                    max_value=int(df['total_quantity'].max()),
                    format="%d"
                ),
                "expiry_date": st.column_config.DateColumn("📅 Hạn dùng"),
                "Trạng thái": st.column_config.TextColumn("💡 Trạng thái")
            }
        )

        st.markdown("---")

        # --- 7. CHỨC NĂNG THU HỒI (HÀNH ĐỘNG NHANH) ---
        st.subheader("⚡ Thao tác quản trị")
        c1, c2 = st.columns(2)

        with c1:
            with st.expander("🔄 Thu hồi License từ thiết bị"):
                res_assets = supabase.table("assets").select("id, asset_tag, software_list").execute()
                assets_with_sw = [a for a in res_assets.data if a.get('software_list')]
                
                if assets_with_sw:
                    with st.form("form_harvest"):
                        selected_asset = st.selectbox("Chọn thiết bị thu hồi", assets_with_sw, 
                                                    format_func=lambda x: f"{x['asset_tag']} ({len(x['software_list'])} SW)")
                        sw_to_remove = st.multiselect("Phần mềm cần lấy lại", selected_asset['software_list'])
                        
                        if st.form_submit_button("Xác nhận thu hồi", type="primary"):
                            if sw_to_remove:
                                # Update Asset: Xóa khỏi danh sách cài đặt
                                new_sw_list = [s for s in selected_asset['software_list'] if s not in sw_to_remove]
                                supabase.table("assets").update({"software_list": new_sw_list}).eq("id", selected_asset['id']).execute()
                                
                                # Update License: Hoàn lại số lượng (Cộng kho)
                                for sw in sw_to_remove:
                                    # Kỹ thuật chuyên gia: Dùng lệnh rpc hoặc cập nhật chính xác dựa trên ID
                                    lic_info = df[df['name'] == sw]
                                    if not lic_info.empty:
                                        new_used = max(0, int(lic_info.iloc[0]['used_quantity']) - 1)
                                        supabase.table("licenses").update({"used_quantity": new_used}).eq("name", sw).execute()
                                
                                st.success("Đã hoàn lại bản quyền vào kho!")
                                st.rerun()
                else:
                    st.info("Không có thiết bị nào đang giữ License.")

        with c2:
            with st.expander("🗑️ Xóa phần mềm khỏi danh mục"):
                del_target = st.selectbox("Chọn phần mềm cần xóa", ["-- Chọn --"] + df['name'].tolist())
                if st.button("Xóa vĩnh viễn", type="secondary", use_container_width=True):
                    if del_target != "-- Chọn --":
                        supabase.table("licenses").delete().eq("name", del_target).execute()
                        st.toast(f"Đã xóa {del_target}")
                        st.rerun()

    # --- 8. THÊM MỚI / CẬP NHẬT (UPSERT) ---
    with st.expander("➕ Đăng ký / Gia hạn bản quyền phần mềm"):
        with st.form("form_add_sw"):
            col_a, col_b, col_c = st.columns([2, 1, 1])
            name_in = col_a.text_input("Tên phần mềm (Ví dụ: Microsoft 365 Business)")
            qty_in = col_b.number_input("Tổng số lượng", min_value=1, step=1)
            expiry_in = col_c.date_input("Ngày hết hạn", value=date.today())
            
            if st.form_submit_button("Lưu thông tin bản quyền"):
                if name_in:
                    # Logic Upsert: Nếu trùng tên sẽ cập nhật, không trùng sẽ thêm mới
                    supabase.table("licenses").upsert({
                        "name": name_in.strip(),
                        "total_quantity": qty_in,
                        "expiry_date": str(expiry_in)
                    }, on_conflict="name").execute()
                    st.success(f"Dữ liệu {name_in} đã được đồng bộ!")
                    st.rerun()
                else:
                    st.error("Vui lòng nhập tên phần mềm.")

    if df_raw.empty:
        st.info("📭 Kho bản quyền đang trống. Vui lòng thêm phần mềm đầu tiên để bắt đầu quản lý.")
