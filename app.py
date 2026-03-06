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
    
    # --- PHẦN 1: CHỌN/TẠO NHÂN VIÊN ---
    with st.expander("👤 Bước 1: Thông tin Nhân viên", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        emp_code = c1.text_input("Mã NV (Khóa chính)", placeholder="VD: NV001")
        emp_name = c2.text_input("Họ tên")
        dept = c3.text_input("Bộ phận")
        branch = c4.selectbox("Chi nhánh", ["Nhà máy Long An", "TP.HCM", "Đà Nẵng", "Miền Bắc", "Polypack"])
        
        if st.button("Xác nhận / Cập nhật Nhân viên"):
            if emp_code and emp_name:
                supabase.table("staff").upsert({
                    "employee_code": emp_code, 
                    "full_name": emp_name, 
                    "department": dept,
                    "branch": branch
                }).execute()
                st.success(f"Đã lưu thông tin nhân viên: {emp_name}")
            else:
                st.warning("Vui lòng nhập Mã và Tên nhân viên.")

    # --- PHẦN 2: THÊM THIẾT BỊ CHO NHÂN VIÊN ---
    if emp_code:
        st.divider()
        st.subheader(f"📦 Thêm thiết bị cho [{emp_code}]")
        with st.form("add_asset_form"):
            col_a, col_b, col_c = st.columns(3)
            a_type = col_a.selectbox("Loại thiết bị", ["PC", "LT", "MN", "PR"])
            a_id = col_b.text_input("Số thứ tự (VD: 0001)", value="0001")
            p_date = col_c.date_input("Ngày mua/cấp phát")
            
            full_asset_tag = f"{a_type}{a_id}"
            specs = st.text_input("Cấu hình chi tiết (CPU, RAM, Monitor size...)")
            softs = st.text_area("Danh sách phần mềm (cách nhau bằng dấu phẩy)")
            
            if st.form_submit_button("Lưu tài sản"):
                # Logic khuyến nghị tự động dựa trên loại máy
                recommendation = "Thiết bị hoạt động bình thường."
                if a_type in ["PC", "LT"]:
                    recommendation = "💡 Khuyến nghị: Bảo trì định kỳ mỗi 6 tháng (vệ sinh, tra keo)."

                asset_data = {
                    "asset_tag": full_asset_tag,
                    "type": a_type,
                    "assigned_to_code": emp_code,
                    "specs": {"detail": specs},
                    "software_list": [s.strip() for s in softs.split(",") if s.strip()],
                    "purchase_date": str(p_date),
                    "recommendations": recommendation,
                    "location_id": 1 # Mặc định hoặc lấy theo chi nhánh
                }
                
                try:
                    supabase.table("assets").insert(asset_data).execute()
                    st.success(f"Đã thêm {full_asset_tag} cho nhân viên {emp_code}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

    # --- PHẦN 3: TÌM KIẾM CHI TIẾT ---
    st.divider()
    search = st.text_input("🔍 Tìm nhanh theo Mã NV hoặc Mã Tài sản...")
    if search:
        res = supabase.table("assets").select("*, staff(*)").or_(f"assigned_to_code.eq.{search},asset_tag.ilike.%{search}%").execute()
        if res.data:
            for item in res.data:
                with st.expander(f"📌 {item['asset_tag']} - {item.get('staff', {}).get('full_name', 'N/A')}"):
                    st.write(f"**Cấu hình:** {item['specs'].get('detail', 'N/A')}")
                    st.write(f"**Phần mềm:** {', '.join(item['software_list'])}")
                    st.info(item['recommendations'])

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
