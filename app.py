import streamlit as st
import sys
import os

# Ép Python nhìn thấy thư mục gốc 'quanlytaisan'
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Bây giờ mới thực hiện import các module
from src.database.client import get_supabase
from src.modules import dashboard, inventory, servers, licenses, vault
# ... (phần còn lại của code)
