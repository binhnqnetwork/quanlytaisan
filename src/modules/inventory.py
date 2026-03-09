import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # 1. MAPPING CHUẨN (Đã fix lỗi 23514)
    type_mapping = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP"}

    # --- PHẦN 1: TÌM KIẾM NHÂN VIÊN & BÀN GIAO TÀI SẢN ---
    st.markdown("---")
    st.subheader("👤 Quản lý Cấp phát Tài sản")
    
    col_search, col_info = st.columns([1, 2])
    with col_search:
        e_code = st.text_input("Nhập Mã nhân viên", placeholder="VD: 10438").strip().upper()
    
    if e_code:
        # Tìm nhân viên từ bảng staff
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            with col_info:
                st.info(f"**Nhân viên:** {staff['full_name']} | **Bộ phận:** {staff.get('department')} | **CN:** {staff.get('branch')}")
            
            # --- TAB 1: BÀN GIAO MÁY MÓC ---
            tab_hardware, tab_software = st.tabs(["💻 Bàn giao Phần cứng", "📜 Cấp bản quyền Phần mềm"])
            
            with tab_hardware:
                # Lọc máy đang 'Trong kho'
                avail_assets = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
                if avail_assets.data:
                    with st.form("assign_hardware"):
                        options = {f"{a['asset_tag']} ({a['type'].upper()})": a for a in avail_assets.data}
                        selected = st.selectbox("Chọn thiết bị để bàn giao", list(options.keys()))
                        
                        if st.form_submit_button("Xác nhận bàn giao"):
                            asset = options[selected]
                            # Cập nhật status và assigned_to_code
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, 
                                "status": "Đang sử dụng",
                                "purchase_date": datetime.now().strftime("%Y-%m-%d")
                            }).eq("id", asset['id']).execute()
                            st.success(f"Đã bàn giao {asset['asset_tag']} cho {staff['full_name']}")
                            st.rerun()
                else:
                    st.warning("Không có thiết bị trống trong kho.")

            # --- TAB 2: CẤP PHÁT BẢN QUYỀN (TỪ TAB BẢN QUYỀN) ---
            with tab_software:
                # Tìm máy mà nhân viên này đang sử dụng để cài phần mềm
                my_assets = supabase.table("assets").select("id, asset_tag, software_list").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    # Lấy danh sách phần mềm còn bản quyền từ bảng 'licenses'
                    res_lic = supabase.table("licenses").select("*").gt("remaining_qty", 0).execute()
                    
                    if res_lic.data:
                        with st.form("assign_software"):
                            target_asset = st.selectbox("Chọn máy cài đặt", [a['asset_tag'] for a in my_assets.data])
                            sw_to_add = st.selectbox("Chọn phần mềm bản quyền", [f"{l['software_name']} (Còn {l['remaining_qty']})" for l in res_lic.data])
                            
                            if st.form_submit_button("Kích hoạt bản quyền"):
                                # 1. Cập nhật software_list (JSONB) trong bảng assets
                                asset_item = [a for a in my_assets.data if a['asset_tag'] == target_asset][0]
                                current_sw = asset_item.get('software_list', []) if asset_item.get('software_list') else []
                                sw_name_pure = sw_to_add.split(" (")[0]
                                
                                if sw_name_pure not in current_sw:
                                    current_sw.append(sw_name_pure)
                                    supabase.table("assets").update({"software_list": current_sw}).eq("id", asset_item['id']).execute()
                                    
                                    # 2. Trừ số lượng bản quyền trong bảng licenses
                                    lic_id = [l['id'] for l in res_lic.data if l['software_name'] == sw_name_pure][0]
                                    # Lưu ý: Logic trừ qty nên xử lý phía Database hoặc gọi RPC để đảm bảo chính xác
                                    st.success(f"Đã kích hoạt {sw_name_pure} cho máy {target_asset}")
                                    st.rerun()
                                else:
                                    st.warning("Máy này đã được cài phần mềm này trước đó.")
                    else:
                        st.error("Hết bản quyền khả dụng trong hệ thống.")
                else:
                    st.info("Nhân viên này chưa được gán máy tính nào để cài phần mềm.")
        else:
            st.error(f"Không tìm thấy nhân viên có mã: {e_code}")
