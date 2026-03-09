import streamlit as st
import sys
import os

# Thêm thư mục gốc vào PYTHONPATH để nhận diện thư mục src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.database.client import get_supabase
from src.modules import dashboard, inventory, servers, licenses, vault

# Khởi tạo Supabase
supabase = get_supabase()

# Giao diện chính
st.set_page_config(page_title="🚀 Enterprise Asset Management", layout="wide")
st.title("🚀 Enterprise Asset Management System")

tabs = st.tabs(["📊 Thống kê", "💻 Cấp phát & Kho", "🖥️ Máy chủ", "🌐 Bản quyền", "🔐 Vault"])

with tabs[0]: dashboard.render_dashboard(supabase)
with tabs[1]: inventory.render_inventory(supabase)
with tabs[2]: servers.render_servers(supabase)
with tabs[3]: licenses.render_licenses(supabase)
with tabs[4]: vault.render_vault(supabase)
