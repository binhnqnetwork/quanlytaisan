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
    # Bổ sung ai_advisor vào danh sách import
    from src.modules import dashboard, inventory, servers, licenses, vault, auth, maintenance, ai_advisor
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG & GIAO DIỆN (APPLE STYLE)
st.set_page_config(
    page_title="Asset Management | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nhúng CSS Enterprise Apple
st.markdown("""
    <style>
    /* Font & Nền tổng thể */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #fbfbfd; }
    
    /* Thiết kế Tab chuẩn Apple */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #f5f5f7;
        padding: 8px;
        border-radius: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        border: none !important;
        background-color: transparent !important;
        border-radius: 8px !important;
        padding: 8px 16px !important;
        color: #86868b !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #1d1d1f !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    }

    /* Bo góc cho các Card và Sidebar */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e5e5e7; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e5e7;
        border-radius: 18px;
        padding: 15px !important;
    }
    
    /* Nút bấm Apple Style */
    .stButton>button {
        border-radius: 10px;
        border: none;
        background-color: #0071e3;
        color: white;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #0077ed; opacity: 0.8; }
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
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=60)
        st.markdown(f"### **IT Administrator**")
        st.caption(f"ID: {st.session_state.get('user_email', 'admin@4oranges.com')}")
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
        st.success("● System Online")

    # Header
    st.markdown(f"<h1 style='color: #1d1d1f; font-weight: 700;'>Asset Portfolio Management</h1>", unsafe_allow_html=True)
    st.caption(f"Phiên bản Enterprise 2.1 | Cập nhật lần cuối: {datetime.now().strftime('%H:%M - %d/%m/%Y')}")

    # --- TẠO 7 TABS (BỔ SUNG AI ADVISOR) ---
    tabs = st.tabs([
        "📊 Dashboard", 
        "💻 Inventory", 
        "🖥️ Servers", 
        "🌐 Licenses",
        "🛠️ Maintenance",
        "🔐 Vault",
        "✨ AI Advisor" # Tab mới
    ])

    # Render nội dung
    with tabs[0]: dashboard.render_dashboard(supabase)
    with tabs[1]: inventory.render_inventory(supabase)
    with tabs[2]: servers.render_servers(supabase)
    with tabs[3]: licenses.render_licenses(supabase)
    with tabs[4]: maintenance.render_maintenance(supabase)
    with tabs[5]: vault.render_vault(supabase)
    
    # Render AI Advisor
    with tabs[6]:
        try:
            ai_advisor.render_ai_advisor(supabase)
        except Exception as e:
            st.error(f"❌ AI Module Error: {e}")
