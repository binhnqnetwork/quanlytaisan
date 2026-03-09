import streamlit as st
from src.database.client import get_supabase
from src.modules import dashboard, inventory, servers, licenses, vault

st.set_page_config(page_title="EAM System", layout="wide")
supabase = get_supabase()

# Menu điều hướng chuẩn chuyên nghiệp
tabs = st.tabs(["📊 Thống kê", "💻 Cấp phát & Kho", "🖥️ Máy chủ", "🌐 Bản quyền", "🔐 Vault"])

with tabs[0]: dashboard.render_dashboard(supabase)
with tabs[1]: inventory.render_inventory(supabase)
with tabs[2]: servers.render_servers(supabase)
with tabs[3]: licenses.render_licenses(supabase)
with tabs[4]: vault.render_vault(supabase)
