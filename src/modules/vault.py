import streamlit as st
import pandas as pd
from src.utils.helpers import encrypt_pw, decrypt_pw

def render_vault(supabase):
    # 1. KHỞI TẠO TRẠNG THÁI QUẢN TRỊ
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    # 2. GIAO DIỆN ĐĂNG NHẬP (CĂN GIỮA)
    if not st.session_state.admin_authenticated:
        st.markdown("### 🔐 Xác thực quyền Quản trị viên")
        
        # Sử dụng columns để căn giữa form đăng nhập
        _, col_mid, _ = st.columns([1, 2, 1])
        
        with col_mid:
            with st.container(border=True):
                st.info("Vui lòng nhập mật khẩu Master để truy cập các tính năng chuyên sâu (Xóa/Sửa).")
                admin_pw = st.text_input("Master Password", type="password", placeholder="••••••••")
                
                if st.button("🔓 Mở khóa hệ thống", use_container_width=True, type="primary"):
                    # Bạn nên thay 'Admin@123' bằng mã bảo mật thực tế hoặc cấu hình từ .env
                    if admin_pw == "Admin@123":
                        st.session_state.admin_authenticated = True
                        st.success("Xác thực thành công!")
                        st.rerun()
                    else:
                        st.error("Mật khẩu không chính xác!")
        return # Dừng render các nội dung bên dưới nếu chưa đăng nhập

    # 3. GIAO DIỆN SAU KHI ĐĂNG NHẬP THÀNH CÔNG
    st.toast("Đã mở khóa quyền Admin", icon="🔓")
    
    # Nút đăng xuất nhanh ở góc phải hoặc sidebar
    if st.sidebar.button("🔒 Đăng xuất Admin", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.rerun()

    # Chia các chức năng quản trị thành các Tab chuyên sâu
    tab_pw, tab_staff, tab_org = st.tabs([
        "🔑 Kho Mật Khẩu", 
        "👥 Quản lý Nhân sự", 
        "🏢 Cấu trúc Phòng ban"
    ])

    # --- TAB 1: KHO MẬT KHẨU (Nâng cấp thêm nút Xóa) ---
    with tab_pw:
        st.subheader("Quản lý tài khoản bảo mật")
        render_password_management(supabase)

    # --- TAB 2: QUẢN LÝ NHÂN SỰ (Sửa/Xóa chuyên sâu) ---
    with tab_staff:
        st.subheader("Danh sách & Thao tác Nhân sự")
        render_staff_admin(supabase)

    # --- TAB 3: QUẢN LÝ CẤU TRÚC (Tùy biến Branch/Dept) ---
    with tab_org:
        st.subheader("Cấu trúc Chi nhánh & Phòng ban")
        st.info("Tính năng này cho phép bạn thêm mới Chi nhánh (HCM/HN/DN) hoặc Phòng ban vào hệ thống.")
        # Bạn có thể thêm form insert vào bảng tương ứng ở đây

# --- CÁC HÀM BỔ TRỢ (HELPER FUNCTIONS) ---

def render_password_management(supabase):
    """Xử lý phần Vault cũ nhưng có thêm chức năng Xóa"""
    with st.expander("➕ Thêm tài khoản mới", expanded=False):
        with st.form("add_vault_pro"):
            service = st.text_input("Dịch vụ (vCenter, Server...)")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            note = st.text_area("Ghi chú")
            if st.form_submit_button("Lưu dữ liệu"):
                if service and pw:
                    encrypted = encrypt_pw(pw)
                    supabase.table("secret_vault").insert({
                        "service_name": service, "username": user,
                        "encrypted_password": encrypted, "note": note
                    }).execute()
                    st.success("Đã lưu!")
                    st.rerun()

    res = supabase.table("secret_vault").select("*").execute()
    if res.data:
        for item in res.data:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
                c1.markdown(f"**{item['service_name']}**")
                c2.code(item['username'])
                
                if c3.button("👁️", key=f"view_{item['id']}", help="Xem mật khẩu"):
                    st.code(decrypt_pw(item['encrypted_password']))
                
                if c4.button("🗑️", key=f"del_{item['id']}", help="Xóa tài khoản"):
                    supabase.table("secret_vault").delete().eq("id", item['id']).execute()
                    st.rerun()

def render_staff_admin(supabase):
    """Chức năng chuyên sâu để quản lý nhân sự"""
    res = supabase.table("staff").select("*").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        # Form xóa nhân viên
        with st.expander("❌ Chế độ Xóa nhân viên", expanded=False):
            col_sel, col_btn = st.columns([3, 1])
            to_delete = col_sel.selectbox("Chọn nhân viên cần loại bỏ", 
                                          options=df['employee_code'].tolist(),
                                          format_func=lambda x: f"{x} - {df[df['employee_code']==x]['full_name'].iloc[0]}")
            if col_btn.button("XÁC NHẬN XÓA", type="primary", use_container_width=True):
                supabase.table("staff").delete().eq("employee_code", to_delete).execute()
                st.success(f"Đã xóa nhân viên {to_delete}")
                st.rerun()
        
        st.divider()
        st.dataframe(df, use_container_width=True, hide_index=True)
