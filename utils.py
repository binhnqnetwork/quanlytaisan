import hashlib
import base64
from cryptography.fernet import Fernet

def get_cipher():
    # Bước này cực quan trọng: Biến "4Oqlts" thành 32-byte key chuẩn xác
    user_key = st.secrets["ENCRYPTION_KEY"]
    key_32bytes = hashlib.sha256(user_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_32bytes)
    return Fernet(fernet_key)
