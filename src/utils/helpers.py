import streamlit as st
from cryptography.fernet import Fernet
import pandas as pd
from datetime import datetime

# Khởi tạo hoặc lấy khóa mã hóa từ secrets
def get_encryption_key():
    if "FERNET_KEY" in st.secrets:
        return st.secrets["FERNET_KEY"].encode()
    # Nếu chưa có, hướng dẫn người dùng tạo (chỉ dùng cho dev)
    return Fernet.generate_key()

def encrypt_pw(password: str) -> str:
    """Mã hóa mật khẩu sang dạng byte-string"""
    if not password: return ""
    f = Fernet(get_encryption_key())
    return f.encrypt(password.encode()).decode()

def decrypt_pw(token: str) -> str:
    """Giải mã mật khẩu về dạng văn bản thuần túy"""
    if not token: return ""
    try:
        f = Fernet(get_encryption_key())
        return f.decrypt(token.encode()).decode()
    except Exception:
        return "❌ Lỗi giải mã (Sai Key)"

def format_date(date_str):
    """Chuyển đổi date từ DB sang định dạng VN d/m/Y"""
    if not date_str: return "N/A"
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        return date_str
