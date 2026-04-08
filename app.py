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

# 3. CẤU HÌNH TRANG (ÉP BUỘC HIỆN SIDEBAR)
st.set_page_config(
    page_title="Asset Portfolio | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. NÂNG CẤP GIAO DIỆN APPLE DESIGN (FIX SIDEBAR)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, sans-serif !important;
        background-color: #f5f5f7 !important;
    }

    /* 🔴 QUAN TRỌNG: VÔ HIỆU HÓA NÚT ẨN SIDEBAR */
    [data-testid="collapsedControl"] { display: none !important; }
    button[kind="headerNoContext"] { display: none !important; }

    header {visibility: hidden;}
    .main .block-container {padding-top: 2rem;}

    /* Style cho các Selectbox trong Sidebar chuẩn Apple */
    div[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d2d2d7;
        padding-top: 10px;
    }

    /* Nhãn của bộ lọc */
    .filter-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #86868b;
        margin-bottom: 8px;
        margin-top: 20px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Nút bấm Apple Blue */
    .stButton>button {
        width: 100%;
        height: 48px !important;
        border-radius: 12px !important;
        border: none !important;
        background: linear-gradient(135deg, #0071e3, #0585ff) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0,113,227,0.2) !important;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,113,227,0.3) !important;
    }

    /* Bo góc ô nhập liệu sidebar */
    .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important;
        background-color: #f5f5f7 !important;
        border: 1px solid #d2d2d7 !important;
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
    # --- SIDEBAR NAV & FILTERS (KHÔNG THỂ ẨN) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=60)
        st.markdown(f"### **IT Administrator**")
        st.caption(f"ID: {st.session_state.get('user_email', 'admin@4oranges.com')}")
        
        # 1. Nút Đăng xuất (Luôn hiện ở top)
        if st.button("🚪 Đăng xuất hệ thống"):
            st.session_state.authenticated = False
            st.rerun()
        
        st.markdown("---")
        
        # 2. BỘ LỌC CHUẨN APPLE (DỌC)
        st.markdown('<p class="filter-label">🔍 Bộ lọc hệ thống</p>', unsafe_allow_html=True)
        
        st.session_state.filter_branch = st.selectbox(
            "Chi nhánh",
            ["Tất cả chi nhánh", "Long An", "Hồ Chí Minh", "Hà Nội", "Đà Nẵng"],
            label_visibility="visible"
        )
        
        st.session_state.filter_status = st.selectbox(
            "Trạng thái tài sản",
            ["Tất cả", "Sẵn sàng", "Đang sử dụng", "Bảo trì", "Thanh lý"],
            label_visibility="visible"
        )
        
        st.session_state.search_query = st.text_input(
            "Tìm kiếm mã máy",
            placeholder="Ví dụ: LAP-001...",
            label_visibility="visible"
        )

        st.markdown("<br>"*5, unsafe_allow_html=True)
        st.success("● System Healthy")

    # --- MAIN CONTENT AREA ---
    st.markdown("<h1 style='font-size: 2.5rem; font-weight: 700; color: #1d1d1f;'>Management Console</h1>", unsafe_allow_html=True)
    st.caption(f"Enterprise v3.0 | {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
    st.write("##")

    # --- TẠO TABS ĐIỀU HƯỚNG ---
    tabs = st.tabs([
        "📊 Dashboard", "💻 Inventory", "🖥️ Servers", 
        "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"
    ])

    # Render nội dung cho từng Tab
    with tabs[0]: dashboard.render_dashboard(supabase)
    with tabs[1]: inventory.render_inventory(supabase)
    with tabs[2]: servers.render_servers(supabase)
    with tabs[3]: licenses.render_licenses(supabase)
    with tabs[4]: maintenance.render_maintenance(supabase)
    with tabs[5]: vault.render_vault(supabase)
    with tabs[6]:
        try:
            ai_advisor.render_ai_advisor(supabase)
        except Exception as e:
            st.error(f"❌ AI Module Error: {e}")

    # Footer
    st.markdown("""
        <div style='text-align: center; color: #86868b; padding: 40px; font-size: 0.8rem;'>
            &copy; 2026 4 Oranges IT Solution. Designed for High Performance.
        </div>
    """, unsafe_allow_html=True)
