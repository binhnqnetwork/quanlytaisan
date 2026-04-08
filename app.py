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

# 3. CẤU HÌNH TRANG (APPLE STYLE)
st.set_page_config(
    page_title="Asset Management | 4 Oranges",
    page_icon="🍊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 4. DESIGN SYSTEM - UPGRADE FULL CSS (APPLE ENTERPRISE)
st.markdown("""
<style>
/* ===== DESIGN TOKENS ===== */
:root {
    --bg-main: #f5f5f7;
    --bg-card: #ffffff;
    --text-main: #1d1d1f;
    --text-sub: #6e6e73;
    --primary: #0071e3;
    --border: #e5e5e7;
    --radius-xl: 24px;
    --radius-lg: 16px;
    --shadow-soft: 0 6px 20px rgba(0,0,0,0.04);
    --shadow-hover: 0 12px 30px rgba(0,0,0,0.08);
}

/* ===== GLOBAL ===== */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif;
    background: var(--bg-main) !important;
}

header {visibility: hidden;} /* Ẩn Streamlit Header */
.main .block-container {padding-top: 1.5rem;}

/* ===== CARD SYSTEM ===== */
.stMarkdown div[data-testid="stMarkdownContainer"] .card {
    background: var(--bg-card);
    border-radius: var(--radius-xl);
    padding: 24px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-soft);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    margin-bottom: 20px;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-hover);
}

/* ===== KPI COMPONENTS ===== */
.kpi-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: flex-start;
}
.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: var(--text-main);
    line-height: 1.2;
}
.kpi-label {
    font-size: 14px;
    color: var(--text-sub);
    font-weight: 500;
    margin-top: 4px;
}

/* ===== HEADER ===== */
.header-title {
    font-size: 36px;
    font-weight: 700;
    color: var(--text-main);
    letter-spacing: -1px;
}

/* ===== SIDEBAR & NAV ===== */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid var(--border);
}
/* Style cho radio navigation */
div[data-testid="stSidebarUserContent"] .stRadio > label {
    font-weight: 600 !important;
    color: var(--text-main) !important;
}

/* ===== CUSTOM BUTTON ===== */
.stButton>button {
    border-radius: 14px !important;
    height: 48px !important;
    background: linear-gradient(135deg, #0071e3, #00c6ff) !important;
    color: white !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,113,227,0.2) !important;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0,113,227,0.3) !important;
}
</style>
""", unsafe_allow_html=True)

# 5. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try:
        return get_supabase()
    except Exception:
        st.error("⚠️ Database Connection Failed")
        st.stop()

supabase = init_connection()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 6. AUTHENTICATION CHECK
if not st.session_state.authenticated:
    auth.login_page(supabase)
else:
    # --- SIDEBAR NAVIGATION (THAY THẾ TABS) ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/2592/2592261.png", width=80)
        st.markdown("### IT Management")
        
        menu = st.radio(
            "Hệ thống quản trị",
            ["📊 Dashboard", "💻 Inventory", "🖥️ Servers", "🌐 Licenses", "🛠️ Maintenance", "🔐 Vault", "✨ AI Advisor"],
            index=0
        )
        
        st.markdown("---")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
            
        st.caption(f"User: {st.session_state.get('user_email', 'Admin')}")

    # --- 7. HEADER SECTION ---
    h_col1, h_col2 = st.columns([6, 2])
    with h_col1:
        st.markdown("<div class='header-title'>Asset Portfolio</div>", unsafe_allow_html=True)
        st.caption(f"Cập nhật lần cuối: {datetime.now().strftime('%H:%M - %d/%m/%Y')}")
    with h_col2:
        st.markdown("<div style='text-align: right; padding-top: 10px;'><span style='color: #34c759;'>●</span> System Healthy</div>", unsafe_allow_html=True)

    st.write("---")

    # --- 8. KPI ROW (CỐ ĐỊNH Ở TOP) ---
    k1, k2, k3, k4 = st.columns(4)

    def render_kpi_card(col, title, value, color="#0071e3"):
        col.markdown(f"""
        <div class="card kpi-container">
            <div class="kpi-value" style="color: {color};">{value}</div>
            <div class="kpi-label">{title}</div>
        </div>
        """, unsafe_allow_html=True)

    # Lấy nhanh dữ liệu tổng quan để làm KPI (Có thể tối ưu bằng query)
    render_kpi_card(k1, "Tổng tài sản", "1,240")
    render_kpi_card(k2, "Máy chủ Online", "32", color="#34c759")
    render_kpi_card(k3, "License sắp hạn", "12", color="#ff9500")
    render_kpi_card(k4, "Sự cố tồn đọng", "3", color="#ff3b30")

    # --- 9. MAIN CONTENT (DYNAMIC RENDERING) ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.spinner("Đang tải dữ liệu..."):
        clean_menu = menu.split(" ")[1] # Tách bỏ icon để lấy text

        if clean_menu == "Dashboard":
            dashboard.render_dashboard(supabase)

        elif clean_menu == "Inventory":
            inventory.render_inventory(supabase)

        elif clean_menu == "Servers":
            servers.render_servers(supabase)

        elif clean_menu == "Licenses":
            licenses.render_licenses(supabase)

        elif clean_menu == "Maintenance":
            maintenance.render_maintenance(supabase)

        elif clean_menu == "Vault":
            vault.render_vault(supabase)

        elif clean_menu == "Advisor":
            ai_advisor.render_ai_advisor(supabase)

    # --- 10. FOOTER ---
    st.markdown("""
        <div style='text-align: center; color: #86868b; padding-top: 50px; font-size: 0.8rem;'>
            &copy; 2026 4 Oranges IT Enterprise Solution. Built for High Performance.
        </div>
    """, unsafe_allow_html=True)
