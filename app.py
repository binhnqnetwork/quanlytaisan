import streamlit as st
from supabase import create_client
import json
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

# --- TAB 1: NHÂN VIÊN & CẤP PHÁT ---
with tabs[1]:
    st.title("👤 Nhân sự & Tài sản")
    loc_map = {"Nhà máy Long An": 1, "TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}
    branch_list = list(loc_map.keys())

    # Tra cứu thông minh
    e_code = st.text_input("Mã nhân viên", placeholder="VD: NV001").strip().upper()
    
    st_data = {"full_name": "", "department": "", "branch": "Nhà máy Long An", "is_active": True}
    exists = False

    if e_code:
        res = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        if res.data:
            st_data = res.data[0]
            exists = True
            if not st_data.get('is_active', True):
                st.warning("Trạng thái: Đã nghỉ việc")
            else:
                st.success(f"Hồ sơ: {st_data['full_name']}")

    # Form Nhân viên - Thiết kế tối giản
    with st.expander("Sửa đổi thông tin nhân sự", expanded=not exists):
        with st.form("staff_form_apple"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Họ và Tên", value=st_data.get("full_name", ""))
            f_dept = c2.text_input("Phòng ban", value=st_data.get("department", ""))
            
            db_branch = st_data.get("branch", "Nhà máy Long An")
            default_idx = branch_list.index(db_branch) if db_branch in branch_list else 0
            f_branch = c3.selectbox("Chi nhánh", branch_list, index=default_idx)
            
            # Action Buttons
            col_b1, col_b2, _ = st.columns([1, 1, 2])
            if col_b1.form_submit_button("💾 Cập nhật"):
                if e_code and f_name:
                    supabase.table("staff").upsert({
                        "employee_code": e_code, "full_name": f_name, 
                        "department": f_dept, "branch": f_branch, "is_active": True
                    }).execute()
                    st.rerun()

            if exists and col_b2.form_submit_button("🗑️ Nghỉ việc"):
                supabase.table("staff").update({"is_active": False}).eq("employee_code", e_code).execute()
                st.rerun()

    # Cấp phát thiết bị
    if e_code and exists and st_data.get('is_active', True):
        st.markdown("---")
        with st.expander("➕ Cấp thiết bị mới", expanded=False):
            with st.form("asset_assignment_apple"):
                a1, a2, a3 = st.columns(3)
                a_type = a1.selectbox("Loại", ["PC", "LT", "MN", "PR"])
                a_id = a2.text_input("Số thứ tự (4 số)", placeholder="0001")
                a_date = a3.date_input("Ngày cấp")
                
                a_specs = st.text_input("Cấu hình tóm tắt")
                a_softs = st.text_area("Phần mềm (cách nhau bằng dấu phẩy)")
                
                if st.form_submit_button("Xác nhận bàn giao"):
                    a_tag = f"{a_type}{a_id}"
                    soft_list = [s.strip() for s in a_softs.split(",") if s.strip()]
                    payload = {
                        "asset_tag": a_tag, "type": a_type, "assigned_to_code": e_code,
                        "location_id": loc_map.get(f_branch, 1), "purchase_date": str(a_date),
                        "specs": {"detail": a_specs}, "software_list": soft_list,
                        "recommendations": "💡 Bảo trì định kỳ 6 tháng"
                    }
                    try:
                        supabase.table("assets").upsert(payload).execute()
                        st.success(f"Đã bàn giao {a_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    # Danh sách thiết bị hiện có
    if exists:
        st.markdown("#### Thiết bị đang sở hữu")
        as_res = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
        if as_res.data:
            df_view = pd.DataFrame(as_res.data)
            st.dataframe(df_view[['asset_tag', 'type', 'purchase_date', 'recommendations']], use_container_width=True)

# --- TAB 2: MÁY CHỦ (SERVER) ---
# --- TAB 2: MÁY CHỦ (SERVER) ---
with tabs[2]:
    st.title("🖥️ Hệ thống Máy chủ")
    
    # 1. Đăng ký Server mới
    with st.expander("🛠️ Đăng ký Server mới", expanded=False):
        with st.form("server_registration"):
            sv_tag = st.text_input("Mã Server (VD: SRV-01)").upper().strip()
            sv_ip = st.text_input("Địa chỉ IP (Quản lý)")
            sv_role = st.selectbox("Vai trò", ["Database", "Web Server", "App Server", "AD/DNS", "Storage"])
            
            st.write("Cấu hình chi tiết (JSON)")
            # Cấu hình mẫu cho Server
            default_json = {
                "CPU": "16 Cores",
                "RAM": "64GB",
                "OS": "Windows Server 2022",
                "Storage": "1TB NVMe"
            }
            # Lỗi NameError biến mất sau khi bạn 'import json' ở đầu file
            sv_specs_json = st.text_area("Chỉnh sửa cấu hình", value=json.dumps(default_json, indent=4))
            
            if st.form_submit_button("Lưu cấu hình Server"):
                if sv_tag:
                    try:
                        # Kiểm tra định dạng JSON người dùng nhập vào
                        parsed_specs = json.loads(sv_specs_json)
                        
                        supabase.table("assets").upsert({
                            "asset_tag": sv_tag,
                            "type": "Server",
                            "specs": {
                                "ip": sv_ip, 
                                "role": sv_role, 
                                "hardware": parsed_specs
                            },
                            "recommendations": "⚠️ Kiểm tra nhiệt độ và Backup hàng tuần"
                        }).execute()
                        st.success(f"✅ Đã lưu thông tin máy chủ {sv_tag}")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Định dạng JSON không hợp lệ. Vui lòng kiểm tra lại dấu ngoặc và dấu phẩy.")
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                else:
                    st.warning("Vui lòng nhập Mã Server.")

    # 2. Hiển thị danh sách Server dưới dạng Dashboard Card
    st.markdown("### 📋 Danh sách máy chủ hiện có")
    sv_res = supabase.table("assets").select("*").eq("type", "Server").execute()
    
    if sv_res.data:
        for sv in sv_res.data:
            with st.container():
                c1, c2 = st.columns([1, 4])
                with c1:
                    st.info(f"🏷️ {sv['asset_tag']}")
                with c2:
                    # Lấy thông tin từ JSON specs an toàn
                    specs_data = sv.get('specs', {})
                    ip = specs_data.get('ip', 'N/A')
                    role = specs_data.get('role', 'N/A')
                    hw = specs_data.get('hardware', {})
                    
                    st.write(f"**Vai trò:** {role} | **IP:** `{ip}`")
                    # Hiển thị thông số phần cứng từ JSON
                    details = " • ".join([f"{k}: {v}" for k, v in hw.items()])
                    st.caption(f"⚙️ {details}")
                st.markdown("---")
    else:
        st.info("Chưa có máy chủ nào trong hệ thống.")

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
