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
    from src.modules import (
        dashboard, inventory, servers, licenses, 
        vault, auth, maintenance, ai_advisor 
    )
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG & GIAO DIỆN "APPLE STYLE"
st.set_page_config(
    page_title="Asset Management | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nâng cấp giao diện bằng CSS nâng cao
st.markdown("""
    <style>
    /* Tổng thể font và nền */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="st-at"] { font-family: 'Inter', sans-serif; }
    
    .main { background-color: #f5f7f9; }

    /* Nâng cấp Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e6e9ef;
    }
    
    /* Làm đẹp các Tab */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #ffffff;
        border-radius: 10px !important;
        border: 1px solid #e6e9ef !important;
        padding: 0px 20px !important;
        font-weight: 600;
        color: #4b5563;
        transition: all 0.3s ease;
    }

    .stTabs [data-baseweb="tab"]:hover {
        border-color: #ff8c00 !important;
        color: #ff8c00;
    }

    .stTabs [aria-selected="true"] {
        background-color: #ff8c00 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(255, 140, 0, 0.3);
    }

    /* Hiệu ứng đặc biệt cho Tab AI */
    .stTabs [data-baseweb="tab"]:last-child {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }

    /* Metric Card */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #e6e9ef;
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
    # Sidebar: Glassmorphism Design
    with st.sidebar:
        st.markdown("<h2 style='text-align: center;'>🍊</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-weight: 700; font-size: 1.2rem;'>4 ORANGES IT</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.caption("Tài khoản đang đăng nhập:")
        st.markdown(f"**{st.session_state.get('user_email', 'Admin')}**")
        
        st.markdown("---")
        if st.button("🚪 Đăng xuất hệ thống", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
            
        st.markdown("<br>"*10, unsafe_allow_html=True)
        st.divider()
        st.caption("v2.5.0-PRO Early Access")

    # Header: Dashboard Style
    head_col1, head_col2 = st.columns([2, 1])
    with head_col1:
        st.title("🍊 IT Asset Control Center")
        st.markdown(f"Chào buổi sáng, hệ thống đang vận hành với **100% hiệu năng**.")
    
    with head_col2:
        # Đồng hồ và ngày tháng nhỏ gọn bên góc
        st.markdown(f"""
            <div style="text-align: right; padding-top: 20px; color: #6b7280;">
                📅 {datetime.now().strftime('%A, %d/%m/%Y')}<br>
                🕒 Last sync: {datetime.now().strftime('%H:%M:%S')}
            </div>
        """, unsafe_allow_html=True)

    # --- HỆ THỐNG TABS ---
    tabs = st.tabs([
        "📊 Dashboard", 
        "💻 Inventory", 
        "🖥️ Servers", 
        "🌐 Licenses",
        "🛠️ Maintenance", 
        "🔐 Vault",
        "🤖 AI ADVISOR"
    ])

    # Mapping các module để tránh lặp code (Pro-tip)
    modules = {
        0: dashboard.render_dashboard,
        1: inventory.render_inventory,
        2: servers.render_servers,
        3: licenses.render_licenses,
        4: maintenance.render_maintenance,
        5: vault.render_vault,
        6: ai_advisor.render_ai_advisor
    }

    for idx, render_func in modules.items():
        with tabs[idx]:
            try:
                render_func(supabase)
            except Exception as e:
                st.error(f"❌ Error in module {idx}: {str(e)}")

# Footer nhỏ gọn
st.markdown("---")
st.caption("© 2026 IT Department - 4 Oranges Co., Ltd. Confidential.")
