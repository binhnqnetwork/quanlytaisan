import streamlit as st
import pandas as pd
from src.utils.helpers import encrypt_pw, decrypt_pw

def render_vault(supabase):
    # 1. AUTHENTICATION CHECK
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Quản trị hệ thống")
        _, col_mid, _ = st.columns([1, 2, 1])
        with col_mid:
            with st.container(border=True):
                admin_pw = st.text_input("Master Password", type="password")
                if st.button("🔓 Xác thực", use_container_width=True, type="primary"):
                    if admin_pw == "Admin@123":
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else: st.error("Mật khẩu sai!")
        return

    # 2. GIAO DIỆN QUẢN TRỊ SAU KHI MỞ KHÓA
    st.sidebar.success("🔓 Đang trong chế độ Admin")
    if st.sidebar.button("🔒 Thoát Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()

    tab_staff, tab_org, tab_pw = st.tabs(["👥 Quản lý Nhân sự", "🏢 Phòng ban & Chi nhánh", "🔑 Mật khẩu"])

    # Lấy dữ liệu nền
    res_staff = supabase.table("staff").select("*").execute()
    df_staff = pd.DataFrame(res_staff.data)

    # -------------------------------------------------
    # TAB 1: NHÂN SỰ (SỬA & XÓA AN TOÀN)
    # -------------------------------------------------
    with tab_staff:
        if df_staff.empty:
            st.info("Chưa có nhân viên nào.")
        else:
            col_list, col_edit = st.columns([1, 2])
            
            with col_list:
                st.write("**Chọn nhân viên**")
                sel_code = st.radio("Mã NV", df_staff['employee_code'].tolist(), label_visibility="collapsed")
                staff_info = df_staff[df_staff['employee_code'] == sel_code].iloc[0]

            with col_edit:
                st.write(f"**Chỉnh sửa: {staff_info['full_name']}**")
                with st.form("form_edit_staff"):
                    new_name = st.text_input("Họ và tên", value=staff_info['full_name'])
                    new_email = st.text_input("Email", value=staff_info['email'])
                    new_dept = st.selectbox("Phòng ban", sorted(df_staff['department'].unique().tolist()), 
                                            index=sorted(df_staff['department'].unique().tolist()).index(staff_info['department']))
                    
                    if st.form_submit_button("💾 Lưu thay đổi"):
                        supabase.table("staff").update({
                            "full_name": new_name, 
                            "email": new_email,
                            "department": new_dept
                        }).eq("employee_code", sel_code).execute()
                        st.success("Đã cập nhật!") ; st.rerun()

                # XÓA AN TOÀN (SAFE DELETE)
                with st.expander("⚠️ Khu vực nguy hiểm (Xóa nhân sự)"):
                    st.error(f"Thao tác này sẽ gỡ toàn bộ thiết bị khỏi {sel_code} trước khi xóa.")
                    if st.button(f"Xác nhận xóa vĩnh viễn {sel_code}", type="primary"):
                        try:
                            # Bước 1: Gỡ máy khỏi người này (Chống lỗi Foreign Key)
                            supabase.table("assets").update({"assigned_to_code": None}).eq("assigned_to_code", sel_code).execute()
                            # Bước 2: Xóa nhân viên
                            supabase.table("staff").delete().eq("employee_code", sel_code).execute()
                            st.success("Xóa thành công!") ; st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi: {str(e)}")

    # -------------------------------------------------
    # TAB 2: PHÒNG BAN (THÊM/XÓA/SỬA)
    # -------------------------------------------------
    with tab_org:
        st.subheader("Cơ cấu tổ chức")
        depts = sorted(df_staff['department'].unique().tolist())
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**📁 Danh sách Phòng ban**")
            target_dept = st.selectbox("Chọn phòng ban", depts)
            
            new_dept_name = st.text_input("Tên mới cho phòng ban này")
            if st.button("📝 Đổi tên toàn bộ NV thuộc phòng này"):
                supabase.table("staff").update({"department": new_dept_name}).eq("department", target_dept).execute()
                st.success("Đã đồng bộ tên phòng ban mới!") ; st.rerun()

        with c2:
            st.write("**➕ Thêm phòng ban mới**")
            add_dept = st.text_input("Tên phòng ban muốn thêm")
            if st.button("Thêm nhân viên mẫu vào phòng này"):
                # Vì cấu trúc của bạn đang lưu phòng ban trực tiếp trong nhân viên, 
                # nên ta tạo 1 nhân viên placeholder để tạo phòng ban mới
                supabase.table("staff").insert({
                    "employee_code": f"NEW_{add_dept[:3].upper()}",
                    "full_name": "Nhân viên mẫu",
                    "department": add_dept
                }).execute()
                st.success(f"Đã tạo phòng {add_dept}") ; st.rerun()

    # -------------------------------------------------
    # TAB 3: MẬT KHẨU (Vault cũ)
    # -------------------------------------------------
    with tab_pw:
        render_vault_content(supabase) # Hàm xử lý mật khẩu hiện tại của bạn

def render_vault_content(supabase):
    # Copy logic hiển thị mật khẩu Fernet hiện tại của bạn vào đây
    pass
