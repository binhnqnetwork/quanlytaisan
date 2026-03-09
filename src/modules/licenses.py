import streamlit as st
import pandas as pd
from datetime import datetime

def render_licenses(supabase):
    st.markdown('<h1 class="main-header">🔑 License Management</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Quản lý kho phần mềm bản quyền và theo dõi thời hạn gia hạn.</p>', unsafe_allow_html=True)

    # --- 1. FORM NHẬP / CẬP NHẬT LICENSE ---
    with st.expander("＋ Khởi tạo / Cập nhật kho bản quyền", expanded=False):
        with st.form("add_license_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([3, 1, 2])
            l_name = col1.text_input("Tên phần mềm", placeholder="VD: Windows 11 Pro, Adobe CC...")
            l_total = col2.number_input("Tổng số lượng mua", min_value=1, value=100)
            l_expiry = col3.date_input("Ngày hết hạn bản quyền")
            
            # Ngưỡng cảnh báo mặc định là 5
            if st.form_submit_button("Cập nhật vào hệ thống"):
                if l_name:
                    try:
                        supabase.table("licenses").upsert({
                            "name": l_name.strip(),
                            "total_quantity": l_total,
                            "expiry_date": str(l_expiry),
                            "alert_threshold": 5
                        }, on_conflict="name").execute()
                        st.toast(f"Đã cập nhật kho {l_name}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

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
