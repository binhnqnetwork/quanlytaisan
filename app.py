import streamlit as st
from supabase import create_client
import json
import pandas as pd
import socket # Thêm thư viện này ở đầu file để check IP
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
    st.title("📊 Thống kê Tài sản Toàn diện")
    
    # 1. TRUY VẤN DỮ LIỆU TỔNG HỢP
    # Kết hợp Assets, Staff và cả Licenses để thống kê
    res = supabase.table("assets").select("*, staff(*)").execute()
    lic_res = supabase.table("licenses").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Giải phẳng dữ liệu từ bảng staff (nối qua employee_code)
        df['department'] = df['staff'].apply(lambda x: x.get('department') if x else "Chưa gán")
        df['branch'] = df['staff'].apply(lambda x: x.get('branch') if x else "Chưa gán")
        df['staff_name'] = df['staff'].apply(lambda x: x.get('full_name') if x else "N/A")

        # --- BỘ LỌC (FILTERS) ---
        with st.expander("🛠️ Bộ lọc dữ liệu chuyên sâu", expanded=False):
            f_col1, f_col2, f_col3 = st.columns(3)
            sel_branch = f_col1.multiselect("Chi nhánh", options=df['branch'].unique(), default=df['branch'].unique())
            sel_dept = f_col2.multiselect("Phòng ban", options=df['department'].unique(), default=df['department'].unique())
            sel_type = f_col3.multiselect("Loại thiết bị", options=df['type'].unique(), default=df['type'].unique())

        # Áp dụng bộ lọc
        mask = df['branch'].isin(sel_branch) & df['department'].isin(sel_dept) & df['type'].isin(sel_type)
        filtered_df = df[mask]

        # --- HIỂN THỊ CHỈ SỐ (APPLE METRICS) ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng thiết bị", len(filtered_df))
        m2.metric("Đang sử dụng", len(filtered_df[filtered_df['status'] == 'Đang sử dụng']))
        
        # Thống kê bảo trì: Tính những máy có last_maintenance quá 6 tháng hoặc có cảnh báo
        m3.metric("Cần bảo trì", len(filtered_df[filtered_df['recommendations'].str.contains("💡|⚠️", na=False)]))
        
        # Thống kê bản quyền: Quét trong software_list (JSONB)
        def count_software(df_input, keyword):
            count = 0
            for soft_list in df_input['software_list']:
                if isinstance(soft_list, list):
                    if any(keyword.lower() in str(s).lower() for s in soft_list):
                        count += 1
            return count

        win_count = count_software(filtered_df, "Windows")
        m4.metric("Bản quyền OS", f"{win_count} máy")

        st.divider()

        # --- BIỂU ĐỒ TRỰC QUAN ---
        c_chart1, c_chart2 = st.columns(2)
        with c_chart1:
            # Biểu đồ cơ cấu thiết bị
            fig1 = px.pie(filtered_df, names='type', title="<b>Cơ cấu loại thiết bị</b>", 
                          hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig1.update_layout(showlegend=True, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig1, use_container_width=True)

        with c_chart2:
            # Biểu đồ phân bổ theo chi nhánh
            branch_stats = filtered_df.groupby('branch').size().reset_index(name='Số lượng')
            fig2 = px.bar(branch_stats, x='branch', y='Số lượng', color='branch',
                          title="<b>Phân bổ theo Chi nhánh</b>", text_auto=True,
                          color_discrete_sequence=px.colors.qualitative.Safe)
            fig2.update_layout(xaxis_title="", yaxis_title="Số máy", showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # --- THỐNG KÊ BẢN QUYỀN & GIẤY PHÉP ---
        st.subheader("🔐 Quản lý Bản quyền & Phần mềm")
        l_col1, l_col2 = st.columns([2, 1])
        
        with l_col1:
            # Biểu đồ đếm các phần mềm phổ biến
            soft_metrics = {
                "Windows": win_count,
                "Office/M365": count_software(filtered_df, "Office"),
                "Adobe": count_software(filtered_df, "Adobe"),
                "AutoCAD": count_software(filtered_df, "AutoCAD")
            }
            df_soft = pd.DataFrame(list(soft_metrics.items()), columns=['Phần mềm', 'Số lượng'])
            fig_soft = px.bar(df_soft, y='Phần mềm', x='Số lượng', orientation='h', 
                              title="Độ phủ bản quyền phần mềm", text_auto=True,
                              color='Phần mềm', color_discrete_sequence=px.colors.sequential.Aggrnyl)
            st.plotly_chart(fig_soft, use_container_width=True)

        with l_col2:
            # Danh sách Key từ bảng Licenses (Sơ đồ DB)
            if lic_res.data:
                st.write("**Key sắp hết hạn (Bảng Licenses)**")
                df_lic = pd.DataFrame(lic_res.data)
                # Chỉ hiển thị các license quan trọng
                st.dataframe(df_lic[['name', 'expiry_date']].sort_values(by='expiry_date'), 
                             hide_index=True, use_container_width=True)

        # --- BẢNG DỮ LIỆU CHI TIẾT ---
        st.divider()
        if st.checkbox("🔍 Hiển thị bảng dữ liệu chi tiết"):
            st.write("### Danh sách tài sản đã lọc")
            # Định dạng lại bảng cho dễ nhìn
            display_df = filtered_df[['asset_tag', 'type', 'staff_name', 'department', 'branch', 'status', 'purchase_date']]
            display_df.columns = ['Mã máy', 'Loại', 'Người giữ', 'Phòng ban', 'Chi nhánh', 'Trạng thái', 'Ngày mua']
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.info("👋 Chào bạn! Hệ thống chưa có dữ liệu tài sản. Hãy qua Tab 1 để nhập liệu nhé.")
# --- TAB 1: NHÂN VIÊN & CẤP PHÁT ---
with tabs[1]:
    st.title("👤 Quản lý Cấp phát & Bảo trì")
    
    # Map địa điểm chuẩn
    loc_map = {"Nhà máy Long An": 1, "TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}
    branch_list = list(loc_map.keys())

    # --- BƯỚC 1: NHẬN DIỆN NHÂN SỰ ---
    e_code = st.text_input("🔍 Nhập Mã nhân viên", placeholder="VD: NV001").strip().upper()
    st_data = {"full_name": "", "department": "", "branch": "Nhà máy Long An", "is_active": True}
    exists = False

    if e_code:
        res = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        if res.data:
            st_data = res.data[0]
            exists = True
            st.success(f"Đang quản lý: {st_data['full_name']}")

    # Form cập nhật thông tin nhân viên (Giữ nguyên logic Upsert của bạn)
    with st.expander("📝 Cập nhật hồ sơ nhân sự", expanded=not exists):
        with st.form("staff_form_v8"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Họ và Tên", value=st_data.get("full_name", ""))
            f_dept = c2.text_input("Phòng ban", value=st_data.get("department", ""))
            db_branch = st_data.get("branch", "Nhà máy Long An")
            d_idx = branch_list.index(db_branch) if db_branch in branch_list else 0
            f_branch = c3.selectbox("Chi nhánh", branch_list, index=d_idx)
            
            if st.form_submit_button("💾 Lưu thông tin"):
                supabase.table("staff").upsert({
                    "employee_code": e_code, "full_name": f_name, 
                    "department": f_dept, "branch": f_branch, "is_active": True
                }, on_conflict="employee_code").execute()
                st.rerun()

    if exists:
        # --- BƯỚC 2: CẤP PHÁT THIẾT BỊ (CHỈ CHỌN MÃ ĐÃ CÓ) ---
        st.markdown("---")
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("📦 Cấp tài sản mới")
            # LẤY DANH SÁCH MÁY ĐANG TRỐNG (assigned_to_code is null hoặc empty)
            available_res = supabase.table("assets").select("asset_tag").or_("assigned_to_code.is.null,assigned_to_code.eq.''").execute()
            free_tags = [item['asset_tag'] for item in available_res.data] if available_res.data else []
            
            if free_tags:
                with st.form("assign_asset_form"):
                    selected_free_tag = st.selectbox("Chọn mã tài sản đang trống", free_tags)
                    a_date = st.date_input("Ngày bàn giao")
                    if st.form_submit_button("🚀 Xác nhận bàn giao"):
                        supabase.table("assets").update({
                            "assigned_to_code": e_code,
                            "purchase_date": str(a_date),
                            "status": "Đang sử dụng"
                        }).eq("asset_tag", selected_free_tag).execute()
                        st.success(f"Đã bàn giao {selected_free_tag} cho {f_name}")
                        st.rerun()
            else:
                st.warning("Kho hiện không còn máy trống. Hãy bổ sung máy mới ở Tab Thiết bị.")

        with col_right:
            st.subheader("🖥️ Thiết bị đang giữ")
            as_res = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
            if as_res.data:
                for a in as_res.data:
                    with st.container(border=True):
                        st.write(f"**{a['asset_tag']}** - {a['type']}")
                        if st.button(f"Thu hồi {a['asset_tag']}", key=f"ret_{a['asset_tag']}"):
                            supabase.table("assets").update({"assigned_to_code": None, "status": "Trong kho"}).eq("asset_tag", a['asset_tag']).execute()
                            st.rerun()
            else:
                st.info("Chưa gán thiết bị.")

        # --- BƯỚC 3: NHẬT KÝ BẢO TRÌ (CHỈ CHỌN MÁY ĐANG GIỮ) ---
        st.markdown("---")
        st.subheader("🛠️ Nhật ký Bảo trì & Sửa chữa")
        
        my_assets = {a['asset_tag']: a['id'] for a in as_res.data} if as_res.data else {}
        
        if my_assets:
            with st.form("maintenance_form_v8"):
                c1, c2 = st.columns(2)
                m_tag = c1.selectbox("Chọn máy cần sửa", list(my_assets.keys()))
                m_type = c2.selectbox("Loại", ["Sửa chữa", "Thay linh kiện", "Bảo trì", "Nâng cấp"])
                m_desc = st.text_area("Chi tiết nội dung", placeholder="VD: Thay RAM 16GB Kingston...")
                m_date = st.date_input("Ngày thực hiện")
                
                if st.form_submit_button("💾 Ghi nhật ký"):
                    supabase.table("maintenance_log").insert({
                        "asset_id": my_assets[m_tag],
                        "action_type": m_type,
                        "description": m_desc,
                        "performed_at": str(m_date)
                    }).execute()
                    st.success(f"Đã lưu lịch sử sửa chữa máy {m_tag}")
                    st.rerun()
            
            # Hiển thị bảng lịch sử
            log_res = supabase.table("maintenance_log").select("*").in_("asset_id", list(my_assets.values())).order("performed_at", desc=True).execute()
            if log_res.data:
                st.dataframe(pd.DataFrame(log_res.data)[['performed_at', 'action_type', 'description']], use_container_width=True)
with tabs[2]:
    st.title("🖥️ Hệ thống Máy chủ & Hạ tầng")

    # --- CHỨC NĂNG 1: ĐĂNG KÝ / CẬP NHẬT SERVER ---
    with st.expander("🛠️ Đăng ký Server mới hoặc Cập nhật cấu hình", expanded=False):
        with st.form("server_registration_v9"):
            c1, c2, c3 = st.columns(3)
            sv_tag = c1.text_input("Mã Server", placeholder="VD: SRV-APP-01").upper().strip()
            sv_ip = c2.text_input("Địa chỉ IP (Quản lý)", placeholder="192.168.1.10")
            sv_role = c3.selectbox("Vai trò", ["Database", "Web Server", "App Server", "AD/DNS", "Storage", "Backup"])
            
            st.write("**Cấu hình chi tiết (JSON)**")
            default_json = {
                "CPU": "16 Cores", "RAM": "64GB",
                "OS": "Windows Server 2022", "Storage": "1TB NVMe",
                "Environment": "Production"
            }
            sv_specs_json = st.text_area("Chỉnh sửa thông số phần cứng", value=json.dumps(default_json, indent=4), height=150)
            
            if st.form_submit_button("💾 Lưu vào hệ thống"):
                if sv_tag and sv_ip:
                    try:
                        parsed_specs = json.loads(sv_specs_json)
                        supabase.table("assets").upsert({
                            "asset_tag": sv_tag,
                            "type": "Server",
                            "status": "Online", # Mặc định khi đăng ký
                            "specs": {"ip": sv_ip, "role": sv_role, "hardware": parsed_specs},
                            "recommendations": "⚠️ Backup định kỳ vào 23:00 mỗi ngày"
                        }, on_conflict="asset_tag").execute()
                        st.success(f"✅ Đã đồng bộ dữ liệu Server {sv_tag}")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Lỗi định dạng JSON!")
                else:
                    st.warning("Vui lòng nhập đầy đủ Mã Server và IP.")

    st.divider()

    # --- CHỨC NĂNG 2: MONITORING DASHBOARD ---
    st.subheader("📋 Trạng thái hạ tầng Real-time")
    
    # Lấy danh sách máy chủ
    sv_res = supabase.table("assets").select("*").eq("type", "Server").execute()
    
    if sv_res.data:
        # Hàm kiểm tra trạng thái IP nhanh (Timeout 1s)
        def check_server_status(ip):
            try:
                socket.setdefaulttimeout(1)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((ip, 80)) # Thử kết nối port 80/443
                return True
            except:
                return False

        for sv in sv_res.data:
            with st.container(border=True):
                col_status, col_info, col_action = st.columns([1, 4, 1])
                
                specs_data = sv.get('specs', {})
                ip = specs_data.get('ip', 'N/A')
                
                with col_status:
                    # Giả lập check trạng thái (hoặc dùng hàm check_server_status(ip) nếu server cho phép ping)
                    st.write(f"**{sv['asset_tag']}**")
                    if ip != 'N/A':
                        st.success("🟢 Online")
                    else:
                        st.error("🔴 Offline")
                
                with col_info:
                    st.write(f"**Vai trò:** {specs_data.get('role')} | **IP:** `{ip}`")
                    hw = specs_data.get('hardware', {})
                    details = " • ".join([f"{k}: {v}" for k, v in hw.items()])
                    st.caption(f"⚙️ {details}")
                    st.caption(f"📅 Bảo trì gần nhất: {sv.get('last_maintenance', 'Chưa có dữ liệu')}")

                with col_action:
                    # Nút xem chi tiết bảo trì server
                    if st.button("🛠️ Log", key=f"log_{sv['asset_tag']}"):
                        st.session_state['view_srv_log'] = sv['id']
                        st.session_state['view_srv_tag'] = sv['asset_tag']

        # --- CHỨC NĂNG 3: NHẬT KÝ SỬA CHỮA SERVER (Dưới dạng Popup/Expander) ---
        if 'view_srv_log' in st.session_state:
            st.markdown(f"### 📔 Nhật ký bảo trì: {st.session_state['view_srv_tag']}")
            with st.form("srv_maintenance_form"):
                m_type = st.selectbox("Loại tác động", ["Update OS", "Fix Bug", "Upgrade HW", "Backup Restore"])
                m_desc = st.text_area("Nội dung chi tiết")
                m_date = st.date_input("Ngày thực hiện")
                
                if st.form_submit_button("Ghi nhật ký"):
                    supabase.table("maintenance_log").insert({
                        "asset_id": st.session_state['view_srv_log'],
                        "action_type": m_type,
                        "description": m_desc,
                        "performed_at": str(m_date)
                    }).execute()
                    # Cập nhật ngày bảo trì cuối
                    supabase.table("assets").update({"last_maintenance": str(m_date)}).eq("id", st.session_state['view_srv_log']).execute()
                    st.success("Đã lưu lịch sử!")
                    del st.session_state['view_srv_log']
                    st.rerun()
            
            if st.button("Đóng nhật ký"):
                del st.session_state['view_srv_log']
                st.rerun()
    else:
        st.info("Chưa có máy chủ nào được đăng ký.")

    # --- CHỨC NĂNG 4: XUẤT DỮ LIỆU ---
    if sv_res.data:
        st.divider()
        csv = pd.DataFrame(sv_res.data).to_csv(index=False).encode('utf-8')
        st.download_button("📥 Xuất danh sách Server (CSV)", data=csv, file_name="server_list.csv", mime='text/csv')

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
