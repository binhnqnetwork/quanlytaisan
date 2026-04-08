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

# 4. DESIGN SYSTEM (APPLE LUXURY)
st.markdown("""
<style>
    :root {
        --bg-main: #f5f5f7;
        --bg-card: #ffffff;
        --primary: #0071e3;
        --border: #e5e5e7;
        --radius-xl: 24px;
        --shadow-soft: 0 6px 20px rgba(0,0,0,0.04);
    }

    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'SF Pro Display', -apple-system, sans-serif !important;
        background-color: var(--bg-main) !important;
    }

    header {visibility: hidden;}

    /* Card luôn hiển thị cho bộ lọc */
    .filter-panel {
        background: var(--bg-card);
        border-radius: var(--radius-xl);
        padding: 20px;
        border: 1px solid var(--border);
        box-shadow: var(--shadow-soft);
        margin-bottom: 25px;
    }

    .kpi-card {
        background: white;
        border-radius: 20px;
        padding: 20px;
        border: 1px solid var(--border);
        text-align: left;
    }

    /* Đè style cho sidebar menu */
    .stRadio [data-testid="stWidgetLabel"] { display: none; }
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
    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=80)
        st.markdown("### IT Management")
        menu = st.radio("Nav", ["Dashboard", "Inventory", "Servers", "Licenses", "Maintenance", "Vault", "AI Advisor"])
        st.markdown("---")
        if st.button("🚪 Đăng xuất"):
            st.session_state.authenticated = False
            st.rerun()

    # --- MAIN HEADER ---
    col_t, col_s = st.columns([6, 2])
    with col_t:
        st.markdown(f"<h1 style='font-size: 3rem; font-weight: 700; margin-bottom:0;'>{menu}</h1>", unsafe_allow_html=True)
        st.caption(f"Hệ thống quản trị IT 4 Oranges | {datetime.now().strftime('%d/%m/%Y')}")

    # --- 7. KPI QUICK VIEW (LUÔN HIỆN Ở TOP) ---
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown("<div class='kpi-card'><small>TỔNG TÀI SẢN</small><h3>1,240</h3></div>", unsafe_allow_html=True)
    with k2: st.markdown("<div class='kpi-card'><small>MÁY CHỦ</small><h3>32</h3></div>", unsafe_allow_html=True)
    with k3: st.markdown("<div class='kpi-card'><small>LICENSE SẮP HẠN</small><h3 style='color:#ff9500'>12</h3></div>", unsafe_allow_html=True)
    with k4: st.markdown("<div class='kpi-card'><small>TRẠNG THÁI</small><h3 style='color:#34c759'>Healthy</h3></div>", unsafe_allow_html=True)

    st.write("##")

    # --- 8. GLOBAL FILTER PANEL (LUÔN HIỆN) ---
    # Đây là nơi bộ lọc luôn xuất hiện, không cần nhấn mở
    st.markdown("<div class='filter-panel'>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    with f1:
        branch = st.selectbox("📍 Chi nhánh", ["Tất cả", "Long An", "HCM", "Hà Nội", "Đà Nẵng"], label_visibility="collapsed")
    with f2:
        status = st.selectbox("🔄 Trạng thái", ["Tất cả", "Đang sử dụng", "Trong kho", "Bảo trì"], label_visibility="collapsed")
    with f3:
        search = st.text_input("🔍 Tìm nhanh thiết bị...", placeholder="Nhập Asset Tag hoặc Serial...", label_visibility="collapsed")
    with f4:
        st.button("Tải lại ↻", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 9. RENDER MODULES ---
    with st.container():
        if menu == "Dashboard": dashboard.render_dashboard(supabase)
        elif menu == "Inventory": inventory.render_inventory(supabase)
        elif menu == "Servers": servers.render_servers(supabase)
        elif menu == "Licenses": licenses.render_licenses(supabase)
        elif menu == "Maintenance": maintenance.render_maintenance(supabase)
        elif menu == "Vault": vault.render_vault(supabase)
        elif menu == "AI Advisor": ai_advisor.render_ai_advisor(supabase)

    # Footer
    st.markdown("<div style='text-align: center; color: #86868b; padding: 40px;'>&copy; 2026 IT 4 Oranges</div>", unsafe_allow_html=True)
