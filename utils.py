import streamlit as st
from cryptography.fernet import Fernet
import base64

# Hàm tạo key chuẩn từ chuỗi của bạn (để tránh lỗi định dạng)
def get_cipher():
    # Fernet yêu cầu key 32 bytes base64. Ta sẽ hash key của bạn để đảm bảo độ dài.
    import hashlib
    key = hashlib.sha256(st.secrets["4Oqlts"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))

def encrypt_password(password):
    f = get_cipher()
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password):
    f = get_cipher()
    return f.decrypt(encrypted_password.encode()).decode()
