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
    # THÊM 'ai_advisor' VÀO DANH SÁCH IMPORT
    from src.modules import (
        dashboard, inventory, servers, licenses, 
        vault, auth, maintenance, ai_advisor # <--- Thêm ở đây
    )
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG & GIAO DIỆN
st.set_page_config(
    page_title="Quản lý tài sản 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nhúng CSS tùy chỉnh
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #1a73e8; }
    /* Style cho Tab AI đặc biệt */
    button[id*="tabs-bui3-tab-6"] {
        background-color: #f0f2f6 !important;
        border-bottom: 2px solid #764ba2 !important;
    }
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 5. LOGIC HIỂN THỊ CHÍNH
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=50)
        st.markdown(f"### 🛡️ Quản trị viên")
        st.caption(f"Email: {st.session_state.get('user_email', 'N/A')}")
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.info(f"🟢 **Hệ thống:** Online")

    # Header
    st.title("🍊 Quản lý tài sản 4 Oranges")
    st.caption(f"Phiên bản 2.0 Pro | AI Powered | Ngày: {datetime.now().strftime('%d/%m/%Y')}")

    # --- CẬP NHẬT DANH SÁCH TABS (THÊM TAB AI) ---
    tabs = st.tabs([
        "📊 Tổng quan", 
        "💻 Cấp phát", 
        "🖥️ Máy chủ", 
        "🌐 License",
        "🛠️ Bảo trì", 
        "🔐 Vault",
        "🤖 AI ADVISOR" # <--- Tab "Chốt hạ"
    ])

    # Render nội dung từng Module
    with tabs[0]:
        dashboard.render_dashboard(supabase)

    with tabs[1]:
        inventory.render_inventory(supabase)

    with tabs[2]:
        servers.render_servers(supabase)

    with tabs[3]:
        licenses.render_licenses(supabase)

    with tabs[4]:
        maintenance.render_maintenance(supabase)

    with tabs[5]:
        vault.render_vault(supabase)

    # --- RENDER TAB AI ADVISOR ---
    with tabs[6]:
        try:
            ai_advisor.render_ai_advisor(supabase)
        except Exception as e:
            st.error(f"❌ Lỗi AI Engine: {e}")
