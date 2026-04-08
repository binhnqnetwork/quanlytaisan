import streamlit as st
import sys
import os
from datetime import datetime

# 1. CẤU HÌNH HỆ THỐNG & ĐƯỜNG DẪN
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. IMPORT MODULES (Đảm bảo đường dẫn src.modules hoặc tabs chính xác)
try:
    from src.database.client import get_supabase
    from src.modules import dashboard, inventory, servers, licenses, vault, auth, maintenance, ai_advisor
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG - KHÓA SIDEBAR LUÔN MỞ
st.set_page_config(
    page_title="Management Console | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 4. APPLE DESIGN SYSTEM & SIDEBAR LOCK CSS
st.markdown("""
    <style>
    /* Nhúng Font Apple */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, sans-serif !important;
        background-color: #f5f5f7 !important;
    }

    /* 🔴 KHÓA CỨNG SIDEBAR: ẨN NÚT ĐÓNG VÀ MŨI TÊN */
    [data-testid="collapsedControl"], 
    button[kind="headerNoContext"],
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }

    header {visibility: hidden;} /* Ẩn header mặc định */

    /* Thiết kế Sidebar trắng sạch (Apple Style) */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #d2d2d7;
        min-width: 300px !important;
    }

    /* Thẻ Chỉ số (Metric) */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 20px;
        padding: 20px;
        border: 1px solid #e5e5e7;
    }

    /* Nút bấm Apple Blue */
    .stButton>button {
        width: 100%;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #0071e3, #0585ff) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        height: 45px;
    }
    
    /* Khoảng cách cho Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 5. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try: return get_supabase()
    except: return None

supabase = init_connection()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 6. LOGIC HIỂN THỊ
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- 🟢 SIDEBAR (LUÔN HIỆN - KHÔNG THỂ ẨN) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=60)
        st.markdown("## **Management**")
        
        # Nút Đăng xuất
        if st.button("🚪 Đăng xuất"):
            st.session_state.authenticated = False
            st.rerun()
        
        st.markdown("---")
        
        # MENU BỘ LỌC (Chuẩn dọc dưới Đăng xuất)
        st.markdown("### 🔍 **BỘ LỌC HỆ THỐNG**")
        
        # Lưu vào session_state để dùng xuyên suốt các Tab
        st.session_state.f_branch = st.selectbox(
            "📍 Chi nhánh", 
            ["Tất cả chi nhánh", "Long An", "Hồ Chí Minh", "Miền Bắc", "Đà Nẵng"]
        )
        
        st.session_state.f_status = st.selectbox(
            "🔄 Trạng thái", 
            ["Tất cả", "Sẵn sàng", "Đang sử dụng", "Bảo trì", "Thanh lý"]
        )
        
        st.session_state.f_search = st.text_input(
            "⌨️ Truy vấn nhanh", 
            placeholder="Mã máy, Serial..."
        )
        
        st.write("<br>"*5, unsafe_allow_html=True)
        st.success("● Hệ thống ổn định")

    # --- 🔵 VÙNG NỘI DUNG CHÍNH ---
    st.markdown("<h1 style='font-size: 2.8rem; font-weight: 700; margin-bottom:0;'>Console</h1>", unsafe_allow_html=True)
    st.caption(f"Enterprise Portfolio | {datetime.now().strftime('%d/%m/%Y')}")
    st.write("##")

    # TẠO TABS ĐIỀU HƯỚNG
    tabs = st.tabs([
        "📊 Dashboard", "💻 Inventory", "🖥️ Servers", 
        "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"
    ])

    # RENDER TỪNG TAB (Sử dụng dữ liệu từ Bộ lọc Sidebar bên trên)
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
            st.error(f"AI Module: {e}")

    # FOOTER
    st.markdown("""
        <div style='text-align: center; color: #86868b; padding-top: 50px; font-size: 0.8rem;'>
            &copy; 2026 4 Oranges IT Solution. Pro Version.
        </div>
    """, unsafe_allow_html=True)
