import streamlit as st
import pandas as pd
from src.utils.helpers import encrypt_pw, decrypt_pw

def render_vault(supabase):
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Admin Command Center")
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            with st.container(border=True):
                admin_pw = st.text_input("Master Password", type="password")
                if st.button("🔓 Mở khóa", use_container_width=True, type="primary"):
                    if admin_pw == "Admin@123":
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else: st.error("Sai mật khẩu!")
        return

    # Giao diện chính sau khi mở khóa
    st.sidebar.success("🔓 Chế độ Quản trị viên")
    if st.sidebar.button("🔒 Đăng xuất"):
        st.session_state.admin_authenticated = False
        st.rerun()

    tab_staff, tab_org, tab_pw = st.tabs(["👥 Nhân sự", "🏢 Cơ cấu tổ chức", "🔑 Mật khẩu"])

    # -------------------------------------------------
    # TAB 1: QUẢN LÝ NHÂN SỰ (SỬA & XÓA AN TOÀN)
    # -------------------------------------------------
    with tab_staff:
        st.subheader("Quản lý danh sách nhân sự")
        res_staff = supabase.table("staff").select("*").execute()
        df_staff = pd.DataFrame(res_staff.data)

        if not df_staff.empty:
            sel_staff_code = st.selectbox("Chọn nhân viên", df_staff['employee_code'].tolist(),
                                         format_func=lambda x: f"{x} - {df_staff[df_staff['employee_code']==x]['full_name'].iloc[0]}")
            
            staff_data = df_staff[df_staff['employee_code'] == sel_staff_code].iloc[0]

            with st.form(f"edit_staff_{sel_staff_code}"):
                col1, col2 = st.columns(2)
                new_name = col1.text_input("Họ và tên", value=staff_data['full_name'])
                new_email = col2.text_input("Email", value=staff_data['email'])
                
                if st.form_submit_button("💾 Lưu thay đổi"):
                    supabase.table("staff").update({"full_name": new_name, "email": new_email}).eq("employee_code", sel_staff_code).execute()
                    st.success("Cập nhật thành công!")
                    st.rerun()

            # Chức năng Xóa An toàn (Safe Delete)
            with st.expander("⚠️ Khu vực nguy hiểm (Xóa nhân sự)"):
                st.warning(f"Để xóa {sel_staff_code}, hệ thống sẽ tự động gỡ nhân viên này khỏi các thiết bị đang gán.")
                if st.button(f"Xác nhận xóa nhân viên {sel_staff_code}", type="primary"):
                    # Bước 1: Giải phóng tài sản (Set null cho assigned_to_code trong bảng assets)
                    supabase.table("assets").update({"assigned_to_code": None}).eq("assigned_to_code", sel_staff_code).execute()
                    # Bước 2: Xóa nhân viên
                    supabase.table("staff").delete().eq("employee_code", sel_staff_code).execute()
                    st.success("Đã xóa hoàn tất!")
                    st.rerun()

    # -------------------------------------------------
    # TAB 2: QUẢN LÝ CƠ CẤU (PHÒNG BAN / CHI NHÁNH)
    # -------------------------------------------------
    with tab_org:
        # Giả sử bạn có bảng 'departments' và 'branches'
        # Nếu chưa có bảng riêng, ta sẽ thao tác trực tiếp trên list unique của bảng Staff
        st.subheader("Quản trị Phòng ban & Chi nhánh")
        
        col_dept, col_branch = st.columns(2)
        
        with col_dept:
            st.write("**📁 Phòng ban**")
            depts = sorted(df_staff['department'].unique().tolist())
            target_dept = st.selectbox("Chọn phòng ban", depts)
            new_dept_name = st.text_input("Tên phòng ban mới")
            
            c1, c2 = st.columns(2)
            if c1.button("📝 Đổi tên", use_container_width=True):
                supabase.table("staff").update({"department": new_dept_name}).eq("department", target_dept).execute()
                st.success("Đã đổi tên đồng loạt!") ; st.rerun()
                
            if c2.button("🗑️ Xóa", use_container_width=True, help="Chỉ xóa được khi không còn nhân viên"):
                count = len(df_staff[df_staff['department'] == target_dept])
                if count > 0: st.error(f"Còn {count} nhân viên thuộc phòng này!")
                else: st.info("Phòng ban sẽ tự biến mất khi không còn nhân viên.")

    # -------------------------------------------------
    # TAB 3: MẬT KHẨU (Vault cũ)
    # -------------------------------------------------
    with tab_pw:
        render_password_vault_logic(supabase)

def render_password_vault_logic(supabase):
    # (Giữ nguyên phần render mật khẩu của bạn ở đây)
    pass
