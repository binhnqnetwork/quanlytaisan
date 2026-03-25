import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. CSS CUSTOM (CHUẨN APPLE) ---
    st.markdown("""
        <style>
        .apple-card { background: white; border-radius: 15px; padding: 20px; border: 1px solid #d2d2d7; }
        .stMetric { background: #f5f5f7; padding: 15px; border-radius: 12px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU ---
    res = supabase.table("licenses").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. TIÊU ĐỀ & XUẤT BÁO CÁO ---
    c_header, c_export = st.columns([3, 1])
    with c_header:
        st.markdown("## 🌐 Quản lý Bản quyền Enterprise")
    with c_export:
        if not df.empty:
            csv = df.to_csv(index=False).encode('utf-16')
            st.download_button("📥 Xuất báo cáo Excel", data=csv, file_name=f"License_Report_{date.today()}.csv", mime='text/csv')

    if not df.empty:
        # Xử lý logic tính toán
        df['total_quantity'] = df['total_quantity'].fillna(0).astype(int)
        df['used_quantity'] = df['used_quantity'].fillna(0).astype(int)
        df['remaining'] = df['total_quantity'] - df['used_quantity']
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        
        # Xác định 3 vấn đề cần xử lý (Cảnh báo: Khả dụng <= 0 hoặc Sắp hết hạn < 30 ngày)
        today = date.today()
        issues_df = df[(df['remaining'] <= 0) | ((df['expiry_date'] - today).dt.days <= 30)]
        num_issues = len(issues_df)

        # --- 4. HIỂN THỊ KPI ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng phần mềm", len(df))[cite: 8]
        col2.metric("Tổng bản quyền", df['total_quantity'].sum())[cite: 8]
        col3.metric("⚠️ Cần xử lý", num_issues, delta=f"{num_issues} rủi ro", delta_color="inverse")[cite: 8]
        usage = (df['used_quantity'].sum() / df['total_quantity'].sum() * 100) if df['total_quantity'].sum() > 0 else 0
        col4.metric("Tỷ lệ sử dụng", f"{usage:.1f}%")[cite: 8]

        # --- 5. DANH SÁCH CHI TIẾT (VIỆT HÓA CỘT) ---
        st.markdown("### 📋 Danh sách chi tiết")
        st.dataframe(
            df[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("🏷️ Tên phần mềm"),
                "total_quantity": st.column_config.NumberColumn("🔢 Tổng số"),
                "used_quantity": st.column_config.NumberColumn("📤 Đã cấp"),
                "remaining": st.column_config.ProgressColumn("🟢 Khả dụng", min_value=0, max_value=int(df['total_quantity'].max())),
                "expiry_date": st.column_config.DateColumn("📅 Ngày hết hạn")
            }
        )

        # --- 6. CHỨC NĂNG THU HỒI (FIXED) ---
        st.markdown("---")
        with st.expander("🔄 THU HỒI BẢN QUYỀN (Từ máy hỏng/Nhân viên nghỉ)"):
            res_assets = supabase.table("assets").select("id, asset_tag, software_list").execute()
            assets_with_sw = [a for a in res_assets.data if a.get('software_list')]
            
            if assets_with_sw:
                with st.form("harvest_form"):
                    selected_asset = st.selectbox("Chọn thiết bị nguồn", assets_with_sw, format_func=lambda x: x['asset_tag'])
                    sw_to_remove = st.multiselect("Chọn phần mềm cần thu hồi", selected_asset['software_list'])
                    
                    if st.form_submit_button("Xác nhận thu hồi ngay"):
                        # Cập nhật Assets
                        new_list = [s for s in selected_asset['software_list'] if s not in sw_to_remove]
                        supabase.table("assets").update({"software_list": new_list}).eq("id", selected_asset['id']).execute()
                        # Cập nhật License số lượng
                        for sw in sw_to_remove:
                            lic = supabase.table("licenses").select("id, used_quantity").eq("name", sw).execute()
                            if lic.data:
                                supabase.table("licenses").update({"used_quantity": max(0, lic.data[0]['used_quantity'] - 1)}).eq("id", lic.data[0]['id']).execute()
                        st.success("Đã thu hồi thành công!")
                        st.rerun()

        # --- 7. THÊM / CẬP NHẬT (FIXED) ---
        with st.expander("＋ Thêm / Cập nhật phần mềm"):
            with st.form("add_sw_form"):
                n = st.text_input("Tên phần mềm")
                q = st.number_input("Tổng số lượng", min_value=1)
                d = st.date_input("Ngày hết hạn")
                if st.form_submit_button("Lưu vào hệ thống"):
                    supabase.table("licenses").upsert({"name": n, "total_quantity": q, "expiry_date": str(d)}, on_conflict="name").execute()
                    st.rerun()

        # --- 8. GỠ BỎ (FIXED) ---
        with st.expander("🗑️ Gỡ bỏ phần mềm khỏi hệ thống"):
            del_target = st.selectbox("Chọn phần mềm cần xóa", df['name'].tolist())
            if st.button("Xóa vĩnh viễn", type="primary"):
                supabase.table("licenses").delete().eq("name", del_target).execute()
                st.rerun()
