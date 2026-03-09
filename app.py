import streamlit as st
import sys
import os
from datetime import datetime

# 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. IMPORT MODULES
try:
    from src.database.client import get_supabase
    from src.modules import dashboard, inventory, servers, licenses, vault, auth
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG & GIAO DIỆN
st.set_page_config(
    page_title="Quản lý tài sản 4 Oranges",
    page_icon="🍊🍊🍊🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nhúng CSS tùy chỉnh để giao diện "Rực rỡ" hơn
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        border: 1px solid #e1e4e8;
    }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# 4. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try:
        return get_supabase()
    except Exception:
        st.error("⚠️ Không thể kết nối tới cơ sở dữ liệu Supabase.")
        st.stop()

supabase = init_connection()

# Khởi tạo trạng thái đăng nhập
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 5. LOGIC HIỂN THỊ CHÍNH
if not st.session_state.authenticated:
    # Hiển thị trang đăng nhập nếu chưa login
    auth.login_page(supabase)
else:
    # --- GIAO DIỆN SAU KHI ĐĂNG NHẬP THÀNH CÔNG ---
    
    # Sidebar: Thông tin người dùng & Logout
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=50)
        st.markdown(f"### 🛡️ Quản trị viên")
        st.caption(f"Email: {st.session_state.get('user_email', 'N/A')}")
        st.markdown("---")
        
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
            
        st.info(f"🟢 **Trạng thái:** Hệ thống Online")

    # Header ứng dụng
    col_logo, col_title = st.columns([1, 8])
    with col_title:
        st.title("🚀 Enterprise Asset Management System")
        st.caption(f"Hệ thống quản lý tài sản nội bộ | Phiên bản 2.0 | Ngày: {datetime.now().strftime('%d/%m/%Y')}")

    # Khởi tạo Tabs bên trong khối ELSE để tránh lỗi NameError
    tabs = st.tabs([
        "📊 Thống kê Tổng quan", 
        "💻 Cấp phát & Kho", 
        "🖥️ Hạ tầng Máy chủ", 
        "🌐 Bản quyền & License", 
        "👥 Chi tiết Sử dụng",
        "🔐 Vault Mật khẩu"
    ])

    # Render nội dung từng Module
    # Tất cả phải thụt lề vào trong khối 'else'
    
    with tabs[0]:
        try:
            dashboard.render_dashboard(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi Dashboard: {e}")
            st.info("💡 Mẹo: Kiểm tra lại unpack 6 biến trong dashboard.py")

    with tabs[1]:
        try:
            inventory.render_inventory(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi hiển thị Cấp phát: {e}")

    with tabs[2]:
        try:
            servers.render_servers(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi hiển thị Máy chủ: {e}")

    with tabs[3]:
        try:
            licenses.render_licenses(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi hiển thị Bản quyền: {e}")

    with tabs[4]:
        try:
            vault.render_vault(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi hiển thị Vault: {e}")
