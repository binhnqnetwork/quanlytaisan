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
    from src.modules import dashboard, inventory, servers, licenses, vault, auth, maintenance, ai_advisor
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG
st.set_page_config(
    page_title="Asset Portfolio | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. NÂNG CẤP GIAO DIỆN APPLE DESIGN SYSTEM (CSS LUXURY)
st.markdown("""
    <style>
    /* Nhúng Font San Francisco (Apple) */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #f5f5f7 !important;
    }

    /* Ẩn Header mặc định của Streamlit để tạo cảm giác App Native */
    header {visibility: hidden;}
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}

    /* Hiệu ứng Tiêu đề chính cực lớn */
    .main-title {
        font-size: 3.5rem !important;
        font-weight: 700 !important;
        color: #1d1d1f;
        letter-spacing: -1.2px;
        margin-bottom: 0px;
    }

    /* Tab Navigation chuẩn iPadOS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(232, 232, 237, 0.7);
        padding: 10px;
        border-radius: 24px;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 54px !important;
        border: none !important;
        background-color: transparent !important;
        border-radius: 16px !important;
        padding: 0px 24px !important;
        color: #424245 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.2s ease-in-out;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0071e3 !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.06) !important;
        transform: translateY(-1px);
    }

    /* Thẻ chỉ số (Metric Cards) */
    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(210, 210, 215, 0.4);
        border-radius: 28px !important;
        padding: 24px !important;
        box-shadow: 0 8px 30px rgba(0,0,0,0.02);
        backdrop-filter: blur(10px);
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        color: #1d1d1f !important;
    }

    /* Nút bấm Apple Blue (Gradient & Shadow) */
    .stButton>button {
        width: 100%;
        height: 56px !important;
        border-radius: 18px !important;
        border: none !important;
        background: linear-gradient(135deg, #0071e3, #0585ff) !important;
        color: white !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 12px 24px rgba(0,113,227,0.25) !important;
        transition: all 0.3s cubic-bezier(0.165, 0.84, 0.44, 1) !important;
    }
    .stButton>button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 15px 30px rgba(0,113,227,0.35) !important;
    }

    /* Sidebar thiết kế sạch sẽ */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d2d2d7;
    }

    /* Group Container cho các Module */
    .module-card {
        background: #ffffff;
        border-radius: 30px;
        padding: 30px;
        border: 1px solid #e5e5e7;
    }
    </style>
    """, unsafe_allow_html=True)

# 5. KHỞI TẠO KẾT NỐI
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

# 6. LOGIC HIỂN THỊ CHÍNH
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- SIDEBAR NAV ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=70)
        st.markdown(f"## **Admin Panel**")
        st.caption(f"📍 {st.session_state.get('user_email', 'it-admin@4oranges.com')}")
        st.markdown("---")
        
        # Logout button to hơn, bắt mắt hơn
        if st.button("🚪 Đăng xuất tài khoản"):
            st.session_state.authenticated = False
            st.rerun()
            
        st.markdown("<br>"*10, unsafe_allow_html=True)
        st.info("🟢 **Hệ thống:** Vận hành ổn định")

    # --- MAIN CONTENT AREA ---
    # Header Section
    st.markdown("<h1 class='main-title'>Asset Portfolio</h1>", unsafe_allow_html=True)
    st.caption(f"Hệ thống quản trị hạ tầng IT 4 Oranges | {datetime.now().strftime('%A, %d %B %Y')}")
    st.write("##")

    # --- TẠO TABS ĐIỀU HƯỚNG ---
    tabs = st.tabs([
        "📊 Dashboard", 
        "💻 Inventory", 
        "🖥️ Servers", 
        "🌐 Licenses",
        "🛠️ Maintenance",
        "🔐 Vault",
        "✨ AI Advisor"
    ])

    # --- RENDER MODULES ---
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

    with tabs[6]:
        try:
            ai_advisor.render_ai_advisor(supabase)
        except Exception as e:
            st.error(f"❌ AI Module Error: {e}")

    # Footer nhỏ tinh tế
    st.markdown("""
        <div style='text-align: center; color: #86868b; padding: 40px; font-size: 0.8rem;'>
            &copy; 2026 4 Oranges IT Solution. Designed for High Performance.
        </div>
    """, unsafe_allow_html=True)
