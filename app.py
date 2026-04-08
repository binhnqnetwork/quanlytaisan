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

# 4. DESIGN SYSTEM (APPLE LUXURY UPGRADE)
st.markdown("""
<style>
    :root {
        --bg-main: #f5f5f7;
        --bg-card: #ffffff;
        --primary: #0071e3;
        --border: #e5e5e7;
        --radius-lg: 16px;
    }

    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, sans-serif !important;
        background-color: var(--bg-main) !important;
    }

    header {visibility: hidden;}

    /* Sidebar Filter Box */
    .sb-filter-container {
        background-color: #fbfbfd;
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 15px;
        margin-top: 20px;
    }

    /* KPI Card Style */
    .kpi-card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        border: 1px solid var(--border);
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    
    /* Căn chỉnh Sidebar Radio */
    [data-testid="stSidebarNav"] {padding-top: 0rem;}
</style>
""", unsafe_allow_html=True)

# 5. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try: return get_supabase()
    except: st.stop()

supabase = init_connection()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 6. LOGIC HIỂN THỊ CHÍNH
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- SIDEBAR NAVIGATION & FILTERS ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=70)
        st.markdown("### **IT Enterprise**")
        
        # 6.1 Menu điều hướng
        menu = st.radio(
            "DANH MỤC QUẢN LÝ", 
            ["📊 Dashboard", "💻 Inventory", "🖥️ Servers", "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"]
        )
        
        st.markdown("---")
        
        # 6.2 Nút Đăng xuất
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

        # 6.3 BỘ LỌC NẰM DỌC (LUÔN HIỆN DƯỚI ĐĂNG XUẤT)
        st.write("##")
        st.markdown("🔍 **BỘ LỌC HỆ THỐNG**")
        
        # Bọc trong container để tách biệt visual
        with st.container():
            st.session_state.filter_branch = st.selectbox(
                "📍 Chi nhánh", 
                ["Tất cả", "Long An (LA)", "Hồ Chí Minh (HCM)", "Miền Bắc (MB)", "Đà Nẵng (DN)"]
            )
            
            st.session_state.filter_status = st.selectbox(
                "🔄 Trạng thái", 
                ["Tất cả", "Đang sử dụng", "Trong kho", "Bảo trì", "Thanh lý"]
            )
            
            st.session_state.search_query = st.text_input(
                "⌨️ Tìm kiếm nhanh", 
                placeholder="Asset Tag, Serial..."
            )
            
            if st.button("Làm mới dữ liệu ↻", use_container_width=True, type="secondary"):
                st.rerun()

    # --- 7. MAIN CONTENT AREA ---
    # Header Section
    h_col1, h_col2 = st.columns([6, 2])
    with h_col1:
        st.markdown(f"<h1 style='font-size: 3rem; font-weight: 700; color: #1d1d1f; margin-bottom:0;'>{menu.split(' ')[1]}</h1>", unsafe_allow_html=True)
        st.caption(f"Asset Management System | {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
    with h_col2:
        st.markdown("<div style='text-align: right; padding-top: 20px;'><span style='color: #34c759;'>●</span> System Online</div>", unsafe_allow_html=True)

    # --- 8. KPI ROW ---
    st.write("##")
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown("<div class='kpi-card'><small style='color:#86868b'>TỔNG TÀI SẢN</small><h2 style='margin:0'>1,240</h2></div>", unsafe_allow_html=True)
    with k2: st.markdown("<div class='kpi-card'><small style='color:#86868b'>MÁY CHỦ</small><h2 style='margin:0'>32</h2></div>", unsafe_allow_html=True)
    with k3: st.markdown("<div class='kpi-card'><small style='color:#86868b'>LICENSE HẾT HẠN</small><h2 style='margin:0; color:#ff3b30'>12</h2></div>", unsafe_allow_html=True)
    with k4: st.markdown("<div class='kpi-card'><small style='color:#86868b'>KHU VỰC</small><h2 style='margin:0'>04</h2></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 9. DYNAMIC MODULE RENDERING ---
    # Lấy tên menu sạch để render
    module_name = menu.split(" ")[1]
    
    with st.container():
        if module_name == "Dashboard": dashboard.render_dashboard(supabase)
        elif module_name == "Inventory": inventory.render_inventory(supabase)
        elif module_name == "Servers": servers.render_servers(supabase)
        elif module_name == "Licenses": licenses.render_licenses(supabase)
        elif module_name == "Maintenance": maintenance.render_maintenance(supabase)
        elif module_name == "Vault": vault.render_vault(supabase)
        elif module_name == "Advisor": ai_advisor.render_ai_advisor(supabase)

    # Footer
    st.markdown("<div style='text-align: center; color: #86868b; padding: 40px; font-size: 0.8rem;'>&copy; 2026 4 Oranges IT Solution</div>", unsafe_allow_html=True)
