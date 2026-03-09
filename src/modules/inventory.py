import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. GIAO DIỆN APPLE-STYLE ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: #ffffff; border-radius: 18px; padding: 24px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
        }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .badge-blue { background: #e8f2ff; color: #0066cc; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700; color: #1d1d1f;">📦 Hệ thống Quản trị Tài sản</h1>', unsafe_allow_html=True)

    # --- 2. TỰ ĐỘNG FIX LỖI "assets_type_check" ---
    # Ánh xạ từ nhãn hiển thị sang mã máy (Constraint yêu cầu)
    type_mapping = {
        "Laptop": "LT",
        "Desktop PC": "PC",
        "Monitor": "MN",
        "Server": "SV",
        "Khác": "OT"
    }

    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 3])
            new_tag = col1.text_input("Asset Tag", placeholder="VD: PC0001")
            selected_label = col2.selectbox("Phân loại", list(type_mapping.keys()))
            new_specs = col3.text_input("Cấu hình tóm tắt")
            
            if st.form_submit_button("Xác nhận Nhập kho"):
                if new_tag:
                    try:
                        # Dùng mã 'LT', 'PC'... để không vi phạm constraint
                        db_value = type_mapping[selected_label]
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": db_value, 
                            "status": "Trong kho",
                            "specs": {"note": new_specs}
                        }).execute()
                        st.success(f"✅ Đã nhập kho thiết bị {new_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    # --- 3. QUẢN LÝ NHÂN SỰ & ĐĂNG KÝ MỚI ---
    st.markdown("### 👤 Quản lý theo Nhân sự")
    e_code = st.text_input("Mã nhân viên", placeholder="Nhập mã nhân viên (VD: 10438)").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge badge-blue">Thành viên hệ thống</span>
                    <h2 style="margin: 10px 0 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">📍 {staff.get('department')} | {staff.get('branch')}</p>
                </div>
            """, unsafe_allow_html=True)
            # Code hiển thị thiết bị và bàn giao (giữ nguyên logic cũ)...
        else:
            st.warning(f"Mã **{e_code}** chưa tồn tại.")
            with st.expander(f"🆕 Tạo hồ sơ nhân sự mới: {e_code}", expanded=True):
                with st.form("new_staff_form"):
                    new_name = st.text_input("Họ và Tên")
                    c1, c2 = st.columns(2)
                    
                    # Phòng ban & Chi nhánh theo chuẩn của bạn
                    dept_opts = ["Nhân viên VP", "Kỹ thuật", "Kế toán", "Kinh doanh", "Sản xuất", "Khác (Nhập tay)"]
                    dept_choice = c1.selectbox("Phòng ban", dept_opts)
                    final_dept = c1.text_input("Tên phòng ban cụ thể") if dept_choice == "Khác (Nhập tay)" else dept_choice
                    
                    branch_list = ["Polypack", "Nhà máy LA", "Chi nhánh TPHCM", "Đà Nẵng", "Miền Bắc"]
                    new_branch = c2.selectbox("Chi nhánh", branch_list)
                    
                    if st.form_submit_button("Lưu hồ sơ nhân viên"):
                        if new_name and final_dept:
                            supabase.table("staff").insert({
                                "employee_code": e_code, "full_name": new_name,
                                "department": final_dept, "branch": new_branch
                            }).execute()
                            st.success("Hồ sơ đã được lưu!")
                            st.rerun()
