import streamlit as st
import sys
import os
from datetime import datetime

# 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. IMPORT MODULES (Cập nhật đường dẫn theo cấu hình folder của bạn)
try:
    from src.database.client import get_supabase
    # Đảm bảo các module này nằm trong thư mục src/modules hoặc tabs tùy cấu trúc của bạn
    from src.modules import dashboard, inventory, servers, licenses, vault, auth, maintenance, ai_advisor
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG - QUAN TRỌNG: initial_sidebar_state="expanded"
st.set_page_config(
    page_title="Asset Portfolio | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded" # Đảm bảo bộ lọc luôn hiện khi load trang
)

# 4. DESIGN SYSTEM (APPLE LUXURY - SIDEBAR OPTIMIZED)
st.markdown("""
<style>
    /* Font & Nền */
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', sans-serif !important;
        background-color: #f5f5f7 !important;
    }

    header {visibility: hidden;} /* Ẩn header mặc định */

    /* Tùy chỉnh Sidebar để các ô lọc nhìn to và rõ hơn */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e5e5e7;
    }
    
    .stSelectbox, .stTextInput {
        margin-bottom: 10px !important;
    }

    /* Style cho các thẻ KPI trên Dashboard */
    .kpi-box {
        background: white;
        border: 1px solid #e5e5e7;
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 5. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try:
        return get_supabase()
    except Exception:
        return None

supabase = init_connection()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 6. LOGIC HIỂN THỊ CHÍNH
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- SIDEBAR NAVIGATION & FILTERS (LUÔN HIỆN) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=80)
        st.markdown("### **IT Enterprise**")
        
        # Menu điều hướng
        menu = st.radio(
            "DANH MỤC QUẢN LÝ", 
            ["📊 Dashboard", "💻 Inventory", "🖥️ Servers", "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"]
        )
        
        st.markdown("---")
        
        # Nút Đăng xuất
        if st.button("🚪 Đăng xuất tài khoản", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

        # --- BỘ LỌC DỌC (Dưới nút Đăng xuất) ---
        st.write("##")
        st.markdown("🔍 **BỘ LỌC HỆ THỐNG**")
        
        with st.container():
            # Lưu các giá trị lọc vào session_state để các module con có thể lấy dùng
            st.session_state.filter_branch = st.selectbox(
                "📍 Chi nhánh", 
                ["Tất cả", "Long An", "Hồ Chí Minh", "Miền Bắc", "Đà Nẵng"]
            )
            
            st.session_state.filter_status = st.selectbox(
                "🔄 Trạng thái", 
                ["Tất cả", "Đang sử dụng", "Trong kho", "Bảo trì", "Thanh lý"]
            )
            
            st.session_state.search_query = st.text_input(
                "⌨️ Tìm kiếm mã máy", 
                placeholder="Nhập mã máy..."
            )
            
            if st.button("Làm mới ↻", use_container_width=True):
                st.rerun()

    # --- 7. MAIN CONTENT AREA ---
    # Header & Status
    col_title, col_status = st.columns([6, 2])
    with col_title:
        # Lấy tên menu bỏ icon
        clean_name = menu.split(" ")[1]
        st.markdown(f"<h1 style='font-size: 3rem; font-weight: 700; color: #1d1d1f; margin-bottom:0;'>{clean_name}</h1>", unsafe_allow_html=True)
        st.caption(f"Phiên bản Enterprise 3.0 | {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
    
    with col_status:
        st.markdown("<div style='text-align: right; padding-top: 25px;'><span style='color: #34c759;'>●</span> System Online</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 8. RENDER DYNAMIC MODULES ---
    # Chú ý: Đảm bảo các hàm render trong các file modules chấp nhận tham số (supabase)
    module_key = menu.split(" ")[1]
    
    if module_key == "Dashboard":
        dashboard.render_dashboard(supabase)
    elif module_key == "Inventory":
        inventory.render_inventory(supabase)
    elif module_key == "Servers":
        servers.render_servers(supabase)
    elif module_key == "Licenses":
        licenses.render_licenses(supabase)
    elif module_key == "Maintenance":
        maintenance.render_maintenance(supabase)
    elif module_key == "Vault":
        vault.render_vault(supabase)
    elif module_key == "Advisor":
        ai_advisor.render_ai_advisor(supabase)

    # Footer
    st.markdown(f"<div style='text-align: center; color: #86868b; padding: 40px;'>&copy; 2026 4 Oranges IT Management</div>", unsafe_allow_html=True)
