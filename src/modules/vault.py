import streamlit as st
from src.utils.helpers import encrypt_pw, decrypt_pw

def render_vault(supabase):
    st.subheader("🔐 Kho mật khẩu bảo mật (Mã hóa Fernet)")
    
    # Form thêm tài khoản mới
    with st.expander("➕ Thêm tài khoản mới", expanded=False):
        with st.form("add_vault"):
            service = st.text_input("Dịch vụ (VD: vCenter, AD Admin)")
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            note = st.text_area("Ghi chú")
            
            if st.form_submit_button("Lưu mã hóa"):
                if service and pw:
                    encrypted = encrypt_pw(pw) # Mã hóa trước khi đẩy lên DB
                    supabase.table("secret_vault").insert({
                        "service_name": service,
                        "username": user,
                        "encrypted_password": encrypted,
                        "note": note
                    }).execute()
                    st.success("Đã lưu dữ liệu an toàn!")
                    st.rerun()

    # Hiển thị và Giải mã
    res = supabase.table("secret_vault").select("*").execute()
    if res.data:
        for item in res.data:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.markdown(f"**{item['service_name']}**")
                c2.code(item['username'])
                
                # Nút xem mật khẩu (chỉ giải mã khi nhấn)
                if c3.button("👁️ Xem", key=f"view_pw_{item['id']}"):
                    plain_pw = decrypt_pw(item['encrypted_password'])
                    st.info(f"Mật khẩu là: `{plain_pw}`")
