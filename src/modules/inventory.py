import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. MAPPING CHUẨN (Khớp với dữ liệu viết thường của bạn) ---
    type_mapping = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}

    st.title("🚀 Quản trị Tài sản & Nhân sự")

    # --- 2. TÌM KIẾM HOẶC TẠO NHÂN VIÊN ---
    st.subheader("👤 Thông tin Nhân viên")
    e_code = st.text_input("Nhập Mã nhân viên", placeholder="VD: 10438").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            # --- TRƯỜNG HỢP 1: NHÂN VIÊN ĐÃ TỒN TẠI ---
            staff = res_staff.data[0]
            st.success(f"**Nhân viên:** {staff['full_name']} | **Bộ phận:** {staff.get('department')} | **CN:** {staff.get('branch')}")
            
            tab_hw, tab_sw = st.tabs(["💻 Bàn giao Phần cứng", "📜 Cấp bản quyền Phần mềm"])
            
            # Bàn giao phần cứng
            with tab_hw:
                avail = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("assign_hw"):
                        options = {f"{a['asset_tag']} ({a['type'].upper()})": a for a in avail.data}
                        pick = st.selectbox("Chọn thiết bị", list(options.keys()))
                        if st.form_submit_button("Xác nhận bàn giao"):
                            asset = options[pick]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", asset['id']).execute()
                            st.success(f"Đã giao {asset['asset_tag']}!")
                            st.rerun()
                else:
                    st.info("Không có máy trống.")

            # Cấp bản quyền (Fix lỗi cột licenses)
            with tab_sw:
                # Tìm máy nhân viên đang dùng
                my_assets = supabase.table("assets").select("id, asset_tag, software_list").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    # Lấy danh sách bản quyền (Dùng select * để tránh lỗi sai tên cột qty)
                    res_lic = supabase.table("licenses").select("*").execute()
                    if res_lic.data:
                        with st.form("assign_sw"):
                            target_tag = st.selectbox("Cài lên máy", [a['asset_tag'] for a in my_assets.data])
                            # Hiển thị tên phần mềm (bỏ qua cột remaining_qty nếu chưa chắc chắn tên)
                            lic_choice = st.selectbox("Chọn phần mềm", [l['software_name'] for l in res_lic.data])
                            
                            if st.form_submit_button("Cấp bản quyền"):
                                asset_item = [a for a in my_assets.data if a['asset_tag'] == target_tag][0]
                                current_sw = asset_item.get('software_list') or []
                                if lic_choice not in current_sw:
                                    current_sw.append(lic_choice)
                                    supabase.table("assets").update({"software_list": current_sw}).eq("id", asset_item['id']).execute()
                                    st.success("Đã cập nhật phần mềm!")
                                    st.rerun()
                                else:
                                    st.warning("Máy đã cài phần mềm này.")
                else:
                    st.warning("Nhân viên chưa có máy để cài phần mềm.")

        else:
            # --- TRƯỜNG HỢP 2: NHÂN VIÊN CHƯA TỒN TẠI (TẠO MỚI) ---
            st.error(f"Mã nhân viên **{e_code}** chưa có trên hệ thống.")
            with st.expander(f"🆕 Tạo hồ sơ nhân viên mới: {e_code}", expanded=True):
                with st.form("create_staff_form"):
                    new_name = st.text_input("Họ và Tên")
                    c1, c2 = st.columns(2)
                    new_dept = c1.selectbox("Phòng ban", ["IT", "Kế toán", "Kinh doanh", "Sản xuất", "Văn phòng"])
                    new_branch = c2.selectbox("Chi nhánh", list(branch_map.keys()))
                    
                    if st.form_submit_button("Lưu hồ sơ nhân viên"):
                        if new_name:
                            supabase.table("staff").insert({
                                "employee_code": e_code,
                                "full_name": new_name,
                                "department": new_dept,
                                "branch": new_branch
                            }).execute()
                            st.success("Đã tạo nhân viên thành công!")
                            st.rerun()
                        else:
                            st.warning("Vui lòng nhập tên nhân viên.")

    st.markdown("---")
    # Giữ lại phần nhập kho tài sản của bạn ở phía dưới...
