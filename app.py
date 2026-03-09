import streamlit as st
import sys
import os
from datetime import datetime

# 1. CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG
# Đảm bảo Python luôn tìm thấy thư mục 'src' dù chạy ở Local hay Streamlit Cloud
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. IMPORT MODULES (Sau khi đã setup sys.path)
try:
    from src.database.client import get_supabase
    from src.modules import dashboard, inventory, servers, licenses, vault
except ImportError as e:
    st.error(f"❌ Lỗi cấu trúc thư mục: {e}")
    st.stop()

# 3. CẤU HÌNH TRANG & GIAO DIỆN (UI/UX)
st.set_page_config(
    page_title="Enterprise Asset Management",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nhúng CSS để tùy chỉnh giao diện chuyên nghiệp hơn
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px 4px 0px 0px;
        padding: 10px 20px;
        border: 1px solid #e1e4e8;
    }
    .stTabs [aria-selected="true"] { background-color: #e8f0fe !important; border-bottom: 2px solid #1a73e8 !important; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #1a73e8; }
    </style>
    """, unsafe_allow_html=True)

# 4. KHỞI TẠO KẾT NỐI
@st.cache_resource
def init_connection():
    try:
        return get_supabase()
    except Exception as e:
        st.error("⚠️ Không thể kết nối tới cơ sở dữ liệu. Vui lòng kiểm tra Secrets!")
        st.stop()

supabase = init_connection()

# 5. HEADER ỨNG DỤNG
col_logo, col_title = st.columns([1, 8])
with col_title:
    st.title("🚀 Enterprise Asset Management System")
    st.caption(f"Hệ thống quản lý tài sản nội bộ | Phiên bản 2.0 | Ngày: {datetime.now().strftime('%d/%m/%Y')}")

# 6. ĐIỀU HƯỚNG TABS
tabs = st.tabs([
    "📊 Thống kê Tổng quan", 
    "💻 Cấp phát & Kho", 
    "🖥️ Hạ tầng Máy chủ", 
    "🌐 Bản quyền & License", 
    "🔐 Vault Mật khẩu"
])

# 7. RENDER NỘI DUNG THEO Từng MODULE
# Sử dụng try-except cho từng tab để lỗi ở một tab không làm sập toàn bộ app
with tabs[0]:
    try:
        dashboard.render_dashboard(supabase)
    except Exception as e:
        st.error(f"Lỗi hiển thị Thống kê: {e}")

with tabs[1]:
    try:
        inventory.render_inventory(supabase)
    except Exception as e:
        st.error(f"Lỗi hiển thị Cấp phát: {e}")

with tabs[2]:
    try:
        servers.render_servers(supabase)
    except Exception as e:
        st.error(f"Lỗi hiển thị Máy chủ: {e}")

with tabs[3]:
    try:
        licenses.render_licenses(supabase)
    except Exception as e:
        st.error(f"Lỗi hiển thị Bản quyền: {e}")

with tabs[4]:
    try:
        vault.render_vault(supabase)
    except Exception as e:
        st.error(f"Lỗi hiển thị Vault: {e}")

# 8. FOOTER (Tùy chọn)
st.sidebar.markdown("---")
st.sidebar.info(f"👤 **Người vận hành:** Admin\n\n🟢 **Trạng thái:** Kết nối Supabase ổn định")
if st.sidebar.button("🔄 Làm mới dữ liệu"):
    st.cache_resource.clear()
    st.rerun()
