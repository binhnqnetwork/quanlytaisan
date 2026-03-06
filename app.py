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
    st.title("👤 Nhân sự & Thiết bị")
    
    # Map địa điểm dựa trên bảng 'locations' trong hình của bạn
    # Lưu ý: Trong hình, staff và assets đều nối tới locations.id
    loc_map = {"Nhà máy Long An": 1, "TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}
    branch_list = list(loc_map.keys())

    # --- BƯỚC 1: TRA CỨU NHÂN VIÊN ---
    e_code = st.text_input("Mã nhân viên", placeholder="VD: NV001").strip().upper()
    
    st_data = {"full_name": "", "department": "", "branch": "Nhà máy Long An", "is_active": True, "location_id": 1}
    exists = False

    if e_code:
        res = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        if res.data:
            st_data = res.data[0]
            exists = True
            st.success(f"Hồ sơ: {st_data['full_name']}")

    # --- FORM NHÂN VIÊN (Dùng UPSERT để tránh lỗi 23505) ---
    with st.expander("📝 Quản lý hồ sơ nhân sự", expanded=not exists):
        with st.form("staff_form_v7"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Họ và Tên", value=st_data.get("full_name", ""))
            f_dept = c2.text_input("Phòng ban", value=st_data.get("department", ""))
            
            curr_branch = st_data.get("branch", "Nhà máy Long An")
            d_idx = branch_list.index(curr_branch) if curr_branch in branch_list else 0
            f_branch = c3.selectbox("Chi nhánh", branch_list, index=d_idx)
            
            save_btn = st.form_submit_button("💾 Xác nhận Nhân viên (Lưu/Cập nhật)")

            if save_btn:
                if e_code and f_name:
                    # UPSERT: Nếu trùng employee_code sẽ tự động UPDATE
                    supabase.table("staff").upsert({
                        "employee_code": e_code, 
                        "full_name": f_name, 
                        "department": f_dept, 
                        "branch": f_branch,
                        "location_id": loc_map.get(f_branch),
                        "is_active": True
                    }, on_conflict="employee_code").execute()
                    st.success("Dữ liệu nhân sự đã đồng bộ!")
                    st.rerun()

    # --- BƯỚC 2: BỔ SUNG CHỨC NĂNG THÊM THIẾT BỊ ---
    if e_code and exists:
        st.markdown("---")
        st.subheader(f"📦 Cấp thiết bị cho {st_data['full_name']}")
        
        with st.form("asset_add_v7"):
            a1, a2, a3 = st.columns(3)
            a_type = a1.selectbox("Loại thiết bị", ["PC", "LT", "MN", "PR"])
            a_num = a2.text_input("Số thứ tự (4 số)", placeholder="0001")
            a_date = a3.date_input("Ngày bàn giao")
            
            a_specs = st.text_input("Cấu hình (CPU, RAM...)")
            a_softs = st.text_area("Phần mềm cài sẵn (cách nhau bằng dấu phẩy)")
            
            # Cột mới trong DB theo hình: maintenance_history, software_list
            if st.form_submit_button("🚀 Hoàn tất bàn giao"):
                a_tag = f"{a_type}{a_num}"
                s_list = [s.strip() for s in a_softs.split(",") if s.strip()]
                
                asset_payload = {
                    "asset_tag": a_tag,
                    "type": a_type,
                    "assigned_to_code": e_code,
                    "location_id": st_data.get("location_id"),
                    "purchase_date": str(a_date),
                    "specs": {"detail": a_specs},
                    "software_list": s_list,
                    "status": "Đang sử dụng",
                    "recommendations": "💡 Bảo trì 6 tháng/lần" if a_type in ["PC", "LT"] else "Theo dõi định kỳ"
                }
                
                try:
                    # UPSERT cho assets: Trùng asset_tag sẽ tự động UPDATE
                    supabase.table("assets").upsert(asset_payload, on_conflict="asset_tag").execute()
                    st.success(f"Đã cập nhật thiết bị {a_tag} cho {e_code}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi thêm thiết bị: {e}")

    # --- BƯỚC 3: DANH SÁCH THIẾT BỊ ĐANG DÙNG ---
    # --- BỔ SUNG VÀO CUỐI TAB 1 ---
if exists:
    st.markdown("---")
    st.subheader("🛠️ Nhật ký Bảo trì & Sửa chữa")
    
    # Lấy danh sách mã máy của nhân viên này để chọn
    user_asset_tags = [a['asset_tag'] for a in as_res.data] if as_res.data else []
    
    if user_asset_tags:
        with st.form("maintenance_form_apple"):
            c1, c2 = st.columns(2)
            selected_tag = c1.selectbox("Chọn thiết bị", user_asset_tags)
            action_type = c2.selectbox("Loại tác động", ["Sửa chữa", "Thay linh kiện", "Bảo trì định kỳ", "Nâng cấp"])
            
            # Tìm asset_id từ asset_tag để lưu vào bảng maintenance_log
            selected_asset = next(a for a in as_res.data if a['asset_tag'] == selected_tag)
            
            desc = st.text_area("Chi tiết nội dung (VD: Thay SSD Samsung 500GB, nâng RAM 16GB...)")
            m_date = st.date_input("Ngày thực hiện")

            if st.form_submit_button("💾 Lưu nhật ký"):
                try:
                    supabase.table("maintenance_log").insert({
                        "asset_id": selected_asset['id'],
                        "action_type": action_type,
                        "description": desc,
                        "performed_at": str(m_date)
                    }).execute()
                    
                    # Cập nhật ngày bảo trì cuối cùng vào bảng assets
                    supabase.table("assets").update({"last_maintenance": str(m_date)}).eq("id", selected_asset['id']).execute()
                    
                    st.success(f"Đã lưu lịch sử cho {selected_tag}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi: {e}")

        # Hiển thị lịch sử cũ
        st.write("📋 Lịch sử gần đây:")
        log_res = supabase.table("maintenance_log").select("*").in_("asset_id", [a['id'] for a in as_res.data]).order("performed_at", desc=True).execute()
        if log_res.data:
            df_logs = pd.DataFrame(log_res.data)
            st.table(df_logs[['performed_at', 'action_type', 'description']])
    else:
        st.info("Nhân viên này chưa có thiết bị để ghi nhận bảo trì.")
    
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
