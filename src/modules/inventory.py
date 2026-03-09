import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    st.title("👤 Quản lý Cấp phát & Kho thiết bị")
    
    # --- PHẦN MỚI: NHẬP THIẾT BỊ VÀO KHO ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_to_stock"):
            col1, col2 = st.columns(2)
            new_tag = col1.text_input("Mã tài sản (Tag)", placeholder="VD: PC001, LAP05...")
            new_type = col2.selectbox("Loại thiết bị", ["Laptop", "PC Desktop", "Monitor", "Printer", "Other"])
            
            if st.form_submit_button("Lưu vào kho"):
                if new_tag:
                    supabase.table("assets").insert({
                        "asset_tag": new_tag.upper(),
                        "type": new_type,
                        "status": "Trong kho",
                        "assigned_to_code": None # Để trống để hiện ở danh sách cấp phát
                    }).execute()
                    st.success(f"Đã thêm {new_tag} vào kho.")
                    st.rerun()

    # --- PHẦN CẤP PHÁT (Như trong ảnh image_dd223c.png) ---
    e_code = st.text_input("🔍 Tra cứu Mã nhân viên").strip().upper()
    if e_code:
        # Logic hiển thị Cấp tài sản mới và Thiết bị đang giữ (như code cũ của bạn)
        pass
