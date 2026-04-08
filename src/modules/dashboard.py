import streamlit as st
import sys
import os
from datetime import datetime

# Cấu hình đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Import các module (Đảm bảo folder src/modules tồn tại)
try:
    from src.database.client import get_supabase
    from src.modules import dashboard, inventory, servers, licenses, vault, auth, maintenance, ai_advisor
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# CẤU HÌNH TRANG - ÉP BUNG SIDEBAR
st.set_page_config(
    page_title="Asset Portfolio | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS APPLE SYSTEM & SIDEBAR LOCK
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, sans-serif !important;
        background-color: #f5f5f7 !important;
    }

    /* KHÓA CỨNG SIDEBAR - KHÔNG CHO ẨN */
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    header {visibility: hidden;}

    /* Sidebar Style */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d2d2d7;
        padding-top: 20px;
    }

    /* Tab Style */
    .stTabs [data-baseweb="tab-list"] {
        background-color: rgba(232, 232, 237, 0.7);
        padding: 8px;
        border-radius: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

supabase = get_supabase()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- SIDEBAR FILTERS (LUÔN HIỆN) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=60)
        st.markdown("### **IT Management**")
        
        if st.button("🚪 Đăng xuất"):
            st.session_state.authenticated = False
            st.rerun()
        
        st.markdown("---")
        st.markdown("🔍 **BỘ LỌC CHUNG**")
        
        # Lưu vào session_state để dùng cho tất cả các tabs
        st.session_state.global_branch = st.selectbox("📍 Chi nhánh", ["Tất cả", "Long An", "HCM", "Đà Nẵng", "Hà Nội"])
        st.session_state.global_search = st.text_input("⌨️ Tìm nhanh", placeholder="Mã máy hoặc tên...")
        
        st.write("<br>"*5, unsafe_allow_html=True)
        st.info("🟢 Hệ thống trực tuyến")

    # --- MAIN CONTENT ---
    st.markdown(f"<h1 style='font-size: 2.8rem; font-weight: 700;'>Console</h1>", unsafe_allow_html=True)
    st.caption(f"Asset Management | {datetime.now().strftime('%d/%m/%Y')}")

    tabs = st.tabs(["📊 Dashboard", "💻 Inventory", "🖥️ Servers", "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"])

    with tabs[0]:
        dashboard.render_dashboard(supabase)
    with tabs[1]:
        inventory.render_inventory(supabase)
    # ... render các tab khác tương tự
