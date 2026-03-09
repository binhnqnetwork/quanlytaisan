import streamlit as st
import pandas as pd
from datetime import datetime

def render_licenses(supabase):
    st.markdown('<h2 class="main-header">🌐 Quản lý Bản quyền</h2>', unsafe_allow_html=True)
    
    # Form nhập liệu
    with st.expander("＋ Nhập kho bản quyền mới"):
        with st.form("add_lic"):
            col1, col2, col3 = st.columns([3, 1, 2])
            name = col1.text_input("Tên phần mềm")
            total = col2.number_input("Số lượng", min_value=1)
            expiry = col3.date_input("Hết hạn")
            if st.form_submit_button("Lưu"):
                supabase.table("licenses").upsert({
                    "name": name, "total_quantity": total, "expiry_date": str(expiry)
                }).execute()
                st.rerun()

    # Truy vấn dữ liệu
    res = supabase.table("licenses").select("*").execute()
    
    if res.data and len(res.data) > 0:
        df = pd.DataFrame(res.data)
        
        # Đảm bảo các cột có giá trị mặc định nếu bị Null
        df['total_quantity'] = df['total_quantity'].fillna(0).astype(int)
        df['used_quantity'] = df['used_quantity'].fillna(0).astype(int)
        df['Remaining'] = df['total_quantity'] - df['used_quantity']
        
        # Hiển thị bảng với cấu hình cột an toàn
        st.dataframe(
            df[['name', 'total_quantity', 'used_quantity', 'Remaining', 'expiry_date']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": "Phần mềm",
                "total_quantity": "Tổng cấp",
                "used_quantity": "Đã dùng",
                "Remaining": st.column_config.ProgressColumn("Còn lại", min_value=0, max_value=int(df['total_quantity'].max()))
            }
        )
    else:
        st.info("Kho bản quyền đang trống. Vui lòng thêm phần mềm mới.")
    # --- 2. TRUY VẤN & XỬ LÝ DỮ LIỆU ---
    res = supabase.table("licenses").select("*").order("name").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Tính toán các chỉ số quan trọng
        df['Remaining'] = df['total_quantity'] - df['used_quantity']
        df['Status'] = df.apply(lambda x: "🚨 Cần mua thêm" if x['Remaining'] <= x['alert_threshold'] else "✅ Ổn định", axis=1)

        # --- 3. HIỂN THỊ DASHBOARD LICENSE ---
        # Hiển thị các thẻ cảnh báo nhanh (Quick Alerts)
        low_stock = df[df['Remaining'] <= df['alert_threshold']]
        if not low_stock.empty:
            for _, row in low_stock.iterrows():
                st.warning(f"**Cảnh báo hết hạn/số lượng:** {row['name']} chỉ còn lại **{row['Remaining']}** bản quyền (Hết hạn: {row['expiry_date']})")

        # Layout bảng dữ liệu chuyên nghiệp
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        
        # Định dạng hiển thị bảng
        display_df = df[['name', 'total_quantity', 'used_quantity', 'Remaining', 'expiry_date', 'Status']]
        display_df.columns = ['Phần mềm', 'Tổng cấp', 'Đã dùng', 'Còn lại', 'Ngày hết hạn', 'Trạng thái']
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Còn lại": st.column_config.ProgressColumn(
                    "Tỉ lệ còn lại",
                    help="Số lượng bản quyền khả dụng trong kho",
                    format="%d",
                    min_value=0,
                    max_value=int(df['total_quantity'].max()),
                ),
                "Trạng thái": st.column_config.TextColumn("Tình trạng"),
                "Ngày hết hạn": st.column_config.DateColumn("Hạn dùng")
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 4. THỐNG KÊ CHI TIẾT THE
