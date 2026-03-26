import streamlit as st
from supabase import create_client, Client
from streamlit_option_menu import option_menu # Cần pip install streamlit-option-menu

# 1. IMPORT CÁC MODULE TỪ THƯ MỤC SRC
from src.modules.dashboard import render_dashboard
from src.modules.inventory import render_inventory
from src.modules.servers import render_servers
from src.modules.licenses import render_licenses
from src.modules.vault import render_vault
from src.modules.maintenance import render_maintenance  # Module mới của chúng ta

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Hệ thống Quản lý Tài sản 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- KẾT NỐI SUPABASE (Dùng Singleton để tối ưu) ---
@st.cache_resource
def init_connection():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    return create_client(url, key)

supabase = init_connection()

# --- GIAO DIỆN HEADER ---
def render_header():
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #FF8C00;">🍊 Quản lý tài sản 4 Oranges</h1>
            <p style="color: #666;">Phiên bản 2.0 | Hệ thống vận hành IT nội bộ</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

def main():
    render_header()

    # --- THANH NAVIGATION (Sử dụng Option Menu cho chuyên nghiệp) ---
    # Bạn có thể dùng st.tabs nếu không muốn cài thêm thư viện
    selected = option_menu(
        menu_title=None,
        options=["Thống kê", "Cấp phát & Kho", "Hạ tầng Server", "Bản quyền", "Bảo trì & Vận hành", "Vault Mật khẩu"],
        icons=["speedometer2", "laptop", "hdd-stack", "patch-check", "tools", "shield-lock"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",
        styles={
            "container": {"padding": "0!important", "background-color": "#fafafa"},
            "icon": {"color": "orange", "font-size": "18px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#eee"},
            "nav-link-selected": {"background-color": "#FF8C00"},
        }
    )

    # --- LOGIC ĐIỀU PHỐI TAB ---
    try:
        if selected == "Thống kê":
            render_dashboard(supabase)
            
        elif selected == "Cấp phát & Kho":
            render_inventory(supabase)
            
        elif selected == "Hạ tầng Server":
            render_servers(supabase)
            
        elif selected == "Bản quyền":
            render_licenses(supabase)
            
        elif selected == "Bảo trì & Vận hành":
            # Gọi module bảo trì mới
            render_maintenance(supabase)
            
        elif selected == "Vault Mật khẩu":
            render_vault(supabase)
            
    except Exception as e:
        st.error(f"❌ Có lỗi xảy ra tại phân hệ {selected}: {str(e)}")
        st.info("Vui lòng kiểm tra lại cấu trúc bảng trong Supabase hoặc liên hệ Admin.")

if __name__ == "__main__":
    main()
