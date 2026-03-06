import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px # Thêm thư viện này vào requirements.txt
from datetime import datetime, timedelta
from utils import encrypt_pw, decrypt_pw

# Cấu hình hệ thống
st.set_page_config(page_title="Kỹ sư Trưởng - Quản lý Tài sản", layout="wide")
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- CSS Custom cho chuẩn Pro ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Enterprise Asset Management System")

# Menu điều hướng
tabs = st.tabs(["📊 Thống kê Tổng quan", "💻 Thiết bị & Nhân viên", "🖥️ Máy chủ", "🌐 Bản quyền", "🔐 Vault"])

# --- TAB 0: THỐNG KÊ CHUẨN PRO ---
with tabs[0]:
    st.header("📈 Dashboard Phân tích")
    res = supabase.table("assets").select("*, locations(name)").execute()
    if res.data:
        df_all = pd.DataFrame(res.data)
        df_all['location_name'] = df_all['locations'].apply(lambda x: x['name'] if x else "N/A")
        
        # Row 1: Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng thiết bị", len(df_all))
        m2.metric("Máy chủ", len(df_all[df_all['type'] == 'Server']))
        m3.metric("Laptop/PC", len(df_all[df_all['type'] != 'Server']))
        
        # Row 2: Charts
        c1, c2 = st.columns(2)
        with c1:
            fig_loc = px.pie(df_all, names='location_name', title="Phân bổ theo địa điểm", hole=0.4)
            st.plotly_chart(fig_loc, use_container_width=True)
        with c2:
            fig_type = px.bar(df_all.groupby('type').size().reset_index(name='count'), 
                             x='type', y='count', title="Số lượng theo loại", color='type')
            st.plotly_chart(fig_type, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu để thống kê.")

# --- TAB 1: THIẾT BỊ & NHÂN VIÊN (Có Tìm kiếm & Nhập liệu) ---
with tabs[1]:
    col_f, col_l = st.columns([1, 2])
    with col_f:
        st.subheader("➕ Thêm Thiết bị")
        with st.form("form_asset"):
            tag = st.text_input("Mã tài sản (Asset Tag)")
            a_type = st.selectbox("Loại", ["Laptop", "PC", "Mobile"])
            loc_id = st.number_input("Location ID (1-5)", min_value=1, max_value=5)
            if st.form_submit_button("Lưu thiết bị"):
                supabase.table("assets").insert({"asset_tag": tag, "type": a_type, "location_id": loc_id}).execute()
                st.success("Đã thêm!")

    with col_l:
        st.subheader("🔍 Danh sách & Tìm kiếm")
        search_q = st.text_input("Tìm kiếm theo Mã tài sản...", key="search_asset")
        query = supabase.table("assets").select("*").neq("type", "Server")
        if search_q:
            query = query.ilike("asset_tag", f"%{search_q}%")
        data = query.execute().data
        if data: st.dataframe(pd.DataFrame(data), use_container_width=True)

# --- TAB 2: MÁY CHỦ (Quản lý cấu hình JSON) ---
with tabs[2]:
    st.subheader("🖥️ Quản lý Máy chủ")
    with st.expander("➕ Cài đặt Server mới"):
        with st.form("form_server"):
            s_tag = st.text_input("Server Tag")
            cpu = st.text_input("CPU")
            ram = st.text_input("RAM")
            if st.form_submit_button("Triển khai Server"):
                specs = {"cpu": cpu, "ram": ram}
                supabase.table("assets").insert({"asset_tag": s_tag, "type": "Server", "specs": specs, "location_id": 1}).execute()
                st.rerun()
    
    search_srv = st.text_input("🔍 Tìm tên Server...")
    srv_data = supabase.table("assets").select("*").eq("type", "Server").ilike("asset_tag", f"%{search_srv}%").execute().data
    st.table(srv_data)

# --- TAB 3: BẢN QUYỀN (Nhắc hẹn & Tìm kiếm) ---
with tabs[3]:
    st.subheader("🌐 Quản lý License/Domain")
    with st.expander("➕ Thêm Bản quyền"):
        with st.form("form_lic"):
            l_name = st.text_input("Tên phần mềm/Domain")
            l_date = st.date_input("Ngày hết hạn")
            if st.form_submit_button("Thêm theo dõi"):
                supabase.table("licenses").insert({"name": l_name, "expiry_date": str(l_date)}).execute()
    
    search_lic = st.text_input("🔍 Tìm kiếm Bản quyền...")
    # Hiển thị logic nhắc hẹn như các bước trước...

# --- TAB 4: VAULT (Mã hóa) ---
with tabs[4]:
    st.subheader("🔐 Kho mật khẩu bí mật")
    # Code Vault của bạn ở bước trước đã rất tốt, chỉ cần thêm ô Search
    search_v = st.text_input("🔍 Tìm dịch vụ...")
    # ... logic hiển thị kết quả lọc theo search_v
