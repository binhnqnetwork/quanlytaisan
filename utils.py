import streamlit as st
from cryptography.fernet import Fernet
import hashlib
import base64

def get_cipher():
    # Biến key "4Oqlts" thành 32-byte key chuẩn
    raw_key = st.secrets["ENCRYPTION_KEY"]
    hashed_key = hashlib.sha256(raw_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(hashed_key))

def encrypt_pw(password):
    if not password: return ""
    return get_cipher().encrypt(password.encode()).decode()

def decrypt_pw(encrypted_text):
    try:
        return get_cipher().decrypt(encrypted_text.encode()).decode()
    except:
        return "❌ Sai Key hoặc lỗi dữ liệu"
