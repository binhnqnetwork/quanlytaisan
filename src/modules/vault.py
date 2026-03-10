import streamlit as st
import pandas as pd
from src.utils.helpers import encrypt_pw, decrypt_pw

def render_vault(supabase):
    st.header("🔐 Admin Command Center")
    
    # 1. CƠ CHẾ XÁC THỰC QUYỀN (ADMIN AUTH)
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        with st.center(): # Giả định bạn có helper căn giữa hoặc dùng columns
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.warning("Vui lòng xác thực quyền quản trị để truy cập các chức năng chuyên sâu.")
                admin_pw = st.text_input("Nhập Password Master", type="password")
                if st.button("Mở khóa hệ thống", use_container_width=True):
                    # Thay 'Admin@123' bằng biến môi trường hoặc cấu hình bảo mật của bạn
                    if admin_pw == "Admin@123": 
                        st.session_state.admin_authenticated = True
                        st.rerun()
                    else:
                        st.error("Sai mật khẩu quản trị!")
        return # Dừng render nếu chưa auth

    # --- NẾU ĐÃ ĐĂNG NHẬP THÀNH CÔNG ---
    
    st.sidebar.success("✅ Đã xác thực quyền Admin")
    if st.sidebar.button("Đăng xuất Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()

    tab_vault, tab_staff_mgmt, tab_dept_mgmt = st.tabs([
        "🔑 Kho Mật Khẩu", "👥 Quản lý Nhân sự", "🏢 Quản lý Cấu trúc"
    ])

    # -------------------------------------------------
    # TAB 1: KHO MẬT KHẨU (Giữ nguyên logic cũ của bạn)
    # -------------------------------------------------
    with tab_vault:
        render_password_vault(supabase)

    # -------------------------------------------------
    # TAB 2: QUẢN LÝ NHÂN SỰ (Sửa/Xóa chuyên sâu)
    # -------------------------------------------------
    with tab_staff_mgmt:
        st.subheader("🛠️ Thao tác nhân sự hệ thống")
        res_staff = supabase.table("staff").select("*").execute()
        df_staff = pd.DataFrame(res_staff.data)

        if not df_staff.empty:
            # Chọn nhân viên để xử lý
            target_staff = st.selectbox("Chọn nhân viên để xử lý", 
                                        options=df_staff['employee_code'].tolist(),
                                        format_func=lambda x: f"{x} - {df_staff[df_staff['employee_code']==x]['full_name'].iloc[0]}")
            
            col_edit, col_del = st.columns(2)
            with col_edit:
                if st.button("🔄 Cập nhật thông tin", use_container_width=True):
                    st.info("Chức năng cập nhật Form đang được mở...")
                    # Tại đây bạn có thể render một Form sửa dữ liệu
            
            with col_del:
                if st.button("🗑️ XÓA NHÂN VIÊN", type="primary", use_container_width=True):
                    # Logic xóa thực tế
                    supabase.table("staff").delete().eq("employee_code", target_staff).execute()
                    st.success(f"Đã xóa nhân viên {target_staff}")
                    st.rerun()
            
            st.divider()
            st.dataframe(df_staff, use_container_width=True)

    # -------------------------------------------------
    # TAB 3: QUẢN LÝ PHÒNG BAN/CHI NHÁNH
    # -------------------------------------------------
    with tab_dept_mgmt:
        st.subheader("🏢 Quản lý danh mục tổ chức")
        # Logic thêm/xóa phòng ban hoặc chi nhánh tại đây
        st.info("Chức năng đang được đồng bộ với Supabase Schema.")

def render_password_vault(supabase):
    """Hàm phụ tách biệt để code sạch sẽ hơn"""
    with st.expander("➕ Thêm tài khoản mới"):
        with st.form("add_vault_pro"):
            service = st.text_input("Dịch vụ")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Lưu mã hóa"):
                encrypted = encrypt_pw(pw)
                supabase.table("secret_vault").insert({
                    "service_name": service, "username": user, 
                    "encrypted_password": encrypted
                }).execute()
                st.success("Đã lưu!")
                st.rerun()

    res = supabase.table("secret_vault").select("*").execute()
    for item in res.data:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            c1.write(f"**{item['service_name']}**")
            c2.code(item['username'])
            if c3.button("👁️", key=f"v_{item['id']}"):
                st.code(decrypt_pw(item['encrypted_password']))
            if c4.button("🗑️", key=f"d_{item['id']}"):
                supabase.table("secret_vault").delete().eq("id", item['id']).execute()
                st.rerun()
