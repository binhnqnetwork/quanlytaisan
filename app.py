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

# --- TAB 1: THIẾT BI & NHÂN VIÊN (NÂNG CẤP) ---
with tabs[1]:
    st.subheader("👥 Quản lý Nhân viên & Thiết bị")
    
    location_map = {"Nhà máy Long An": 1, "Chi nhánh TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}

    # --- BƯỚC 1: THÔNG TIN NHÂN VIÊN ---
    st.markdown("### 👤 Bước 1: Nhận diện Nhân viên")
    emp_code_input = st.text_input("Nhập Mã nhân viên", placeholder="VD: NV001")
    
    # Biến trung gian để lưu dữ liệu nhân viên
    current_staff = {"full_name": "", "department": "", "branch": "Nhà máy Long An"}
    
    if emp_code_input:
        # Kiểm tra xem nhân viên đã tồn tại chưa
        staff_res = supabase.table("staff").select("*").eq("employee_code", emp_code_input).execute()
        if staff_res.data:
            current_staff = staff_res.data[0]
            st.success(f"🔍 Tìm thấy thông tin: {current_staff['full_name']}")
        else:
            st.info("🆕 Mã nhân viên mới, vui lòng điền thông tin bên dưới.")

    with st.form("staff_form"):
        c1, c2, c3 = st.columns(3)
        emp_name = c1.text_input("Họ tên", value=current_staff["full_name"])
        dept = c2.text_input("Bộ phận", value=current_staff.get("department", ""))
        branch = c3.selectbox("Chi nhánh", list(location_map.keys()), 
                             index=list(location_map.keys()).index(current_staff.get("branch", "Nhà máy Long An")))
        
        if st.form_submit_button("Xác nhận thông tin"):
            supabase.table("staff").upsert({
                "employee_code": emp_code_input, "full_name": emp_name, 
                "department": dept, "branch": branch
            }).execute()
            st.toast("Đã lưu thông tin nhân viên!")

    # --- BƯỚC 2: THÊM THIẾT BỊ ---
    if emp_code_input and emp_name:
        st.divider()
        st.subheader(f"📦 Cấp tài sản cho [{emp_code_input}]")
        with st.form("add_asset_form_v3"):
            col_a, col_b, col_c = st.columns(3)
            # Dùng đúng các mã đã fix trong SQL Constraint
            a_type = col_a.selectbox("Loại", ["PC", "LT", "MN", "PR"]) 
            a_num = col_b.text_input("Số thứ tự (VD: 0001)")
            p_date = col_c.date_input("Ngày cấp phát")
            
            a_tag = f"{a_type}{a_num}"
            specs = st.text_input("Cấu hình (CPU, RAM, SSD...)")
            softs = st.text_area("Phần mềm cài đặt")
            
            if st.form_submit_button("💾 Lưu thiết bị"):
                try:
                    asset_payload = {
                        "asset_tag": a_tag, "type": a_type, "assigned_to_code": emp_code_input,
                        "location_id": location_map[branch],
                        "specs": {"detail": specs},
                        "software_list": [s.strip() for s in softs.split(",") if s.strip()],
                        "recommendations": "💡 Khuyến nghị: Bảo trì sau 6 tháng" if a_type in ["PC", "LT"] else "Theo dõi định kỳ",
                        "purchase_date": str(p_date)
                    }
                    supabase.table("assets").insert(asset_payload).execute()
                    st.success(f"🎉 Đã thêm thành công {a_tag}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

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
