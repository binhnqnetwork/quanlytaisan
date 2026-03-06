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
    st.header("📊 Thống kê Tài sản Toàn diện")
    
    # Lấy dữ liệu gộp từ Assets và Staff
    res = supabase.table("assets").select("*, staff(*)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Giải phẳng dữ liệu nhân viên từ cột lồng
        df['department'] = df['staff'].apply(lambda x: x.get('department') if x else "Chưa gán")
        df['branch'] = df['staff'].apply(lambda x: x.get('branch') if x else "Chưa gán")

        # --- BỘ LỌC (FILTERS) ---
        st.markdown("#### 🛠️ Bộ lọc dữ liệu")
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            sel_branch = st.multiselect("Lọc theo Chi nhánh", options=df['branch'].unique(), default=df['branch'].unique())
        with f_col2:
            sel_dept = st.multiselect("Lọc theo Phòng ban", options=df['department'].unique(), default=df['department'].unique())

        # Áp dụng bộ lọc
        mask = df['branch'].isin(sel_branch) & df['department'].isin(sel_dept)
        filtered_df = df[mask]

        # --- HIỂN THỊ CHỈ SỐ ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng thiết bị (đã lọc)", len(filtered_df))
        m2.metric("Số nhân viên sở hữu", filtered_df['assigned_to_code'].nunique())
        m3.metric("Cần bảo trì", len(filtered_df[filtered_df['recommendations'].str.contains("⚠️", na=False)]))

        # --- BIỂU ĐỒ ---
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            fig1 = px.pie(filtered_df, names='type', title="Cơ cấu loại thiết bị", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c_chart2:
            fig2 = px.bar(filtered_df.groupby('branch').size().reset_index(name='Số lượng'), 
                         x='branch', y='Số lượng', color='branch', title="Phân bổ theo Chi nhánh")
            st.plotly_chart(fig2, use_container_width=True)
            
        # Hiển thị bảng dữ liệu chi tiết bên dưới
        if st.checkbox("Xem danh sách chi tiết"):
            st.dataframe(filtered_df[['asset_tag', 'type', 'assigned_to_code', 'department', 'branch', 'recommendations']])
    else:
        st.info("Chưa có dữ liệu tài sản để thống kê.")

# --- TAB 1: THIẾT BI & NHÂN VIÊN (NÂNG CẤP) ---
with tabs[1]:
    st.subheader("👥 Quản lý Nhân sự & Cấp phát Tài sản")
    
    # Map ID địa điểm như đã tạo ở bước trước
    location_map = {"Nhà máy Long An": 1, "Chi nhánh TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}

    # --- BƯỚC 1: NHẬN DIỆN MÃ NHÂN VIÊN ---
    st.markdown("### 🔍 1. Nhận diện & Chỉnh sửa Nhân viên")
    emp_code_input = st.text_input("Nhập Mã nhân viên (Key chính)", placeholder="VD: NV001").strip()
    
    # Khởi tạo giá trị mặc định cho Form
    current_staff = {"full_name": "", "department": "", "branch": "Nhà máy Long An", "is_active": True}
    is_new_staff = True

    if emp_code_input:
        # Truy vấn kiểm tra nhân viên đã tồn tại chưa
        staff_res = supabase.table("staff").select("*").eq("employee_code", emp_code_input).execute()
        
        if staff_res.data:
            current_staff = staff_res.data[0]
            is_new_staff = False
            if not current_staff.get('is_active', True):
                st.warning(f"⚠️ Nhân viên {current_staff['full_name']} hiện đang ở trạng thái: ĐÃ NGHỈ VIỆC")
            else:
                st.success(f"✅ Đang hiển thị dữ liệu của: {current_staff['full_name']}")
        else:
            st.info("🆕 Mã nhân viên mới. Vui lòng nhập thông tin để thêm vào hệ thống.")

    # --- FORM NHẬP / CHỈNH SỬA NHÂN VIÊN ---
    with st.form("staff_management_form"):
        c1, c2, c3 = st.columns(3)
        emp_name = c1.text_input("Họ và Tên", value=current_staff["full_name"])
        dept = c2.text_input("Bộ phận / Phòng ban", value=current_staff.get("department", ""))
        
        # Xử lý Index cho Selectbox chi nhánh
        branch_list = list(location_map.keys())
        default_branch_idx = branch_list.index(current_staff.get("branch", "Nhà máy Long An"))
        branch = c3.selectbox("Chi nhánh", branch_list, index=default_branch_idx)
        
        col_btn1, col_btn2 = st.columns(2)
        
        # Nút Lưu/Cập nhật
        submit_label = "💾 Lưu nhân viên mới" if is_new_staff else "📝 Cập nhật thông tin"
        if col_btn1.form_submit_button(submit_label):
            if emp_code_input and emp_name:
                supabase.table("staff").upsert({
                    "employee_code": emp_code_input,
                    "full_name": emp_name,
                    "department": dept,
                    "branch": branch,
                    "is_active": True # Tự động active lại nếu có chỉnh sửa
                }).execute()
                st.success("Đã lưu dữ liệu nhân viên thành công!")
                st.rerun()
            else:
                st.error("Vui lòng nhập đầy đủ Mã và Tên nhân viên.")

        # Nút Inactive (Nghỉ việc) - Chỉ hiện khi nhân viên đã tồn tại
        if not is_new_staff:
            if col_btn2.form_submit_button("🗑️ Đánh dấu Nghỉ việc"):
                supabase.table("staff").update({"is_active": False}).eq("employee_code", emp_code_input).execute()
                st.warning(f"Đã chuyển trạng thái nhân viên {emp_name} sang Nghỉ việc.")
                st.rerun()

    # --- BƯỚC 2: CẤP PHÁT THIẾT BỊ (Chỉ hiện khi đã xác định được nhân viên) ---
    if emp_code_input and not is_new_staff and current_staff.get('is_active', True):
        st.divider()
        st.subheader(f"📦 Cấp tài sản cho: {emp_name}")
        
        with st.form("asset_assignment_form"):
            col_a, col_b, col_c = st.columns(3)
            a_type = col_a.selectbox("Loại thiết bị", ["PC", "LT", "MN", "PR"]) 
            a_num = col_b.text_input("Số thứ tự (VD: 0001)")
            p_date = col_c.date_input("Ngày cấp phát")
            
            a_tag = f"{a_type}{a_num}" # Tạo mã chuẩn PC0001
            specs = st.text_input("Cấu hình chi tiết (CPU, RAM, Màn hình...)")
            softs = st.text_area("Danh sách phần mềm (cách nhau bằng dấu phẩy)")
            
            if st.form_submit_button("🚀 Xác nhận cấp thiết bị"):
                try:
                    asset_payload = {
                        "asset_tag": a_tag,
                        "type": a_type,
                        "assigned_to_code": emp_code_input,
                        "location_id": location_map[branch],
                        "specs": {"detail": specs},
                        "software_list": [s.strip() for s in softs.split(",") if s.strip()],
                        "recommendations": "💡 Khuyến nghị: Bảo trì sau 6 tháng" if a_type in ["PC", "LT"] else "Theo dõi định kỳ",
                        "purchase_date": str(p_date)
                    }
                    supabase.table("assets").insert(asset_payload).execute()
                    st.success(f"Đã cấp mã {a_tag} thành công!")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    # --- PHẦN 3: XEM DANH SÁCH THIẾT BỊ ĐANG DÙNG ---
    if emp_code_input and not is_new_staff:
        st.write(f"#### 🖥️ Thiết bị nhân viên này đang sử dụng:")
        user_assets = supabase.table("assets").select("*").eq("assigned_to_code", emp_code_input).execute()
        if user_assets.data:
            df_user = pd.DataFrame(user_assets.data)
            st.table(df_user[['asset_tag', 'type', 'purchase_date', 'recommendations']])
        else:
            st.info("Nhân viên này chưa được cấp thiết bị nào.")

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
