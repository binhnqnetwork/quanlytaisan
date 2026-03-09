import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. MAPPING CHUẨN ĐỂ FIX LỖI 23514 ---
    type_mapping = {
        "Laptop": "LT", "Desktop PC": "PC", "Monitor": "MN", "Server": "SV", "Khác": "OT"
    }
    
    # Mapping hậu tố chi nhánh
    branch_suffixes = {
        "Miền Bắc": "MB", "Miền Nam": "MN", "Miền Trung": "MT", "Nhà máy LA": "LA", "Polypack": "PP"
    }

    with st.expander("📥 Nhập thiết bị mới (Tùy chỉnh Tag)", expanded=True):
        with st.form("pro_add_asset_v2"):
            col1, col2, col3 = st.columns([2, 2, 2])
            
            raw_tag = col1.text_input("Mã số thiết bị", placeholder="VD: PC0001")
            suffix_choice = col2.selectbox("Khu vực (Hậu tố)", list(branch_suffixes.keys()))
            selected_label = col3.selectbox("Phân loại", list(type_mapping.keys()))
            
            # Tự động gợi ý Tag đầy đủ
            full_tag = f"{raw_tag.strip().upper()}-{branch_suffixes[suffix_choice]}"
            st.caption(f"Asset Tag dự kiến: **{full_tag}**")

            if st.form_submit_button("Xác nhận nhập kho"):
                if raw_tag:
                    try:
                        # Gửi 'PC' thay vì 'Desktop PC' để vượt qua constraint
                        db_type = type_mapping[selected_label]
                        
                        supabase.table("assets").insert({
                            "asset_tag": full_tag,
                            "type": db_type, 
                            "status": "Trong kho"
                        }).execute()
                        st.success(f"✅ Đã nhập: {full_tag}")
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
