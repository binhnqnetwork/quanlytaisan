import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Import các module (giả sử bạn đã tạo các file trong src/modules/)
# from src.modules import inventory, servers, licenses, vault

st.set_page_config(page_title="Enterprise Asset Management", layout="wide")

def main():
    st.sidebar.title("🏢 Quản trị Tài sản v1.0")
    
    # 1. Phân quyền đơn giản (Demo)
    menu = ["Dashboard", "Thiết bị & Nhân sự", "Quản lý Server", "Bản quyền & Domain", "Kho mật khẩu (Vault)"]
    choice = st.sidebar.selectbox("Menu hệ thống", menu)

    if choice == "Dashboard":
        render_dashboard()
    elif choice == "Bản quyền & Domain":
        render_license_management()
    # ... tương tự cho các module khác

def render_dashboard():
    st.header("Tổng quan hệ thống")
    col1, col2, col3 = st.columns(3)
    
    # Ví dụ Dashboard metrics
    col1.metric("Tổng thiết bị", "120")
    col2.metric("Server đang chạy", "5")
    col3.metric("Sắp hết hạn (30d)", "3", delta_color="inverse")

def render_license_management():
    st.subheader("🛡️ Quản lý Bản quyền & Domain")
    
    # Logic nhắc hẹn 1 tháng
    today = datetime.now().date()
    next_month = today + timedelta(days=30)
    
    # Giả lập lấy data từ Supabase
    # data = supabase.table("licenses").select("*").execute().data
    # df = pd.DataFrame(data)
    
    st.warning("⚠️ Có 2 Domain sắp hết hạn trong 30 ngày tới!")
    # Hiển thị bảng dữ liệu với Streamlit Data Editor
    # st.data_editor(df)

if __name__ == "__main__":
    main()
