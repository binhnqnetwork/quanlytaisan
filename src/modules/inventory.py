import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH HỆ THỐNG & STYLE APPLE ---
    type_mapping = {
        "Desktop PC": "pc", "Laptop": "laptop", "Server": "server", 
        "Monitor": "monitor", "Máy in laser": "printer_laser",
        "Máy in kim": "printer_dot", "Máy in màu": "printer_color"
    }
    display_type_map = {v: k for k, v in type_mapping.items()}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}
    status_list = ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý", "Đã thanh lý"]

    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: white; border-radius: 18px; padding: 25px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04); border: 1px solid #e5e5e7;
            margin-bottom: 20px;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #f5f5f7; border-radius: 10px 10px 0 0;
            padding: 10px 20px; color: #86868b;
        }
        .stTabs [aria-selected="true"] { background-color: white !important; color: #0071e3 !important; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🍎 Asset Management Pro")
    st.markdown("### Hệ thống Điều phối & Quản trị Tập trung")

    # --- 2. TRUNG TÂM ĐIỀU PHỐI (SEARCH & ASSIGN) ---
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    c_search, c_status = st.columns([2, 1])
    with c_search:
        e_code = st.text_input("🔍 Tra cứu nhân viên", placeholder="Nhập mã nhân viên (VD: 10438)").strip().upper()
    
    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        if res_staff.data:
            staff = res_staff.data[0]
            with c_status:
                st.success(f"Xác thực: {staff['full_name']}")
            st.markdown(f"📂 **Bộ phận:** {staff.get('department')} | 📍 **Vùng:** {staff.get('branch')}")
            st.markdown('</div>', unsafe_allow_html=True)

            t1, t2 = st.tabs(["💻 Bàn giao thiết bị", "📜 Cấp bản quyền"])
            with t1:
                avail = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("assign_hw"):
                        options = {f"{a['asset_tag']} - {display_type_map.get(a['type'])}": a for a in avail.data}
                        pick = st.selectbox("Chọn thiết bị sẵn có", list(options.keys()))
                        if st.form_submit_button("Xác nhận bàn giao"):
                            asset = options[pick]
                            supabase.table("assets").update({"assigned_to_code": e_code, "status": "Đang sử dụng"}).eq("id", asset['id']).execute()
                            st.toast(f"Đã cấp {asset['asset_tag']} cho {staff['full_name']}", icon="✅")
                            st.rerun()
                else: st.info("Kho thiết bị hiện đã trống.")
            
            with t2:
                my_assets = supabase.table("assets").select("id, asset_tag, software_list").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                    with st.form("assign_sw"):
                        target = st.selectbox("Cài đặt lên máy", [a['asset_tag'] for a in my_assets.data])
                        lic_options = {f"{l['name']} (Còn {(l['total_quantity'] or 0)-(l['used_quantity'] or 0)})": l for l in res_lic.data}
                        sw_pick = st.selectbox("Chọn License", list(lic_options.keys()))
                        if st.form_submit_button("Kích hoạt phần mềm"):
                            lic_obj = lic_options[sw_pick]
                            asset_obj = [a for a in my_assets.data if a['asset_tag'] == target][0]
                            sw_list = asset_obj.get('software_list') or []
                            if lic_obj['name'] not in sw_list:
                                sw_list.append(lic_obj['name'])
                                supabase.table("assets").update({"software_list": sw_list}).eq("id", asset_obj['id']).execute()
                                supabase.table("licenses").update({"used_quantity": (lic_obj['used_quantity'] or 0)+1}).eq("id", lic_obj['id']).execute()
                                st.toast("Kích hoạt thành công!", icon="🚀")
                                st.rerun()
                            else: st.warning("Thiết bị này đã có bản quyền này.")
                else: st.warning("Nhân viên này chưa giữ thiết bị nào.")
        else:
            st.markdown('</div>', unsafe_allow_html=True)
            st.error("Mã nhân viên chưa tồn tại.")
            with st.expander("🆕 Tạo hồ sơ nhân sự mới", expanded=True):
                with st.form("new_staff"):
                    n_name = st.text_input("Họ và tên")
                    c1, c2 = st.columns(2)
                    n_dept = c1.text_input("Phòng ban")
                    n_branch = c2.selectbox("Chi nhánh", list(branch_map.keys()))
                    if st.form_submit_button("Lưu nhân viên"):
                        if n_name and n_dept:
                            supabase.table("staff").insert({"employee_code": e_code, "full_name": n_name, "department": n_dept, "branch": n_branch}).execute()
                            st.rerun()
    else: st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. NHẬP KHO (QUY TẮC ĐẶT TÊN CHUẨN) ---
    with st.expander("📥 Nhập thiết bị mới vào kho"):
        with st.form("new_asset"):
            c1, c2, c3 = st.columns(3)
            raw_id = c1.text_input("Số máy (Số thứ tự)")
            area = c2.selectbox("Vùng quản lý", list(branch_map.keys()))
            label = c3.selectbox("Phân loại", list(type_mapping.keys()))
            
            type_code = type_mapping[label]
            short = "LP" if "laser" in type_code else ("DP" if "dot" in type_code else ("CP" if "color" in type_code else type_code[:2].upper()))
            tag_preview = f"{short}{raw_id.strip().upper()}-{branch_map[area]}"
            st.info(f"Mã tài sản sẽ tạo: **{tag_preview}**")
            
            specs = st.text_area("Thông số kỹ thuật")
            if st.form_submit_button("Xác nhận nhập kho"):
                if raw_id:
                    supabase.table("assets").insert({"asset_tag": tag_preview, "type": type_code, "status": "Trong kho", "specs": {"note": specs}}).execute()
                    st.success("Đã nhập kho thành công!")
                    st.rerun()

    # --- 4. BẢNG DANH MỤC GỘP (PEOPLE-CENTRIC VIEW) ---
    st.markdown("---")
    st.markdown("### 📋 Danh sách Quản lý Tài sản")
    
    v_filter = st.segmented_control("Lọc chi nhánh:", ["Tất cả"] + list(branch_map.keys()), default="Tất cả")

    res_all = supabase.table("assets").select("*, staff!assets_assigned_to_code_fkey(full_name, department, branch)").order("asset_tag").execute()
    
    if res_all.data:
        # Gộp dữ liệu: 1 người - n tài sản & n phần mềm
        grouped = {}
        for item in res_all.data:
            s = item.get('staff')
            owner_key = item.get('assigned_to_code') or "KHO_CHUNG"
            
            if owner_key not in grouped:
                grouped[owner_key] = {
                    "Mã NV": owner_key if owner_key != "KHO_CHUNG" else "---",
                    "Nhân viên": s.get('full_name') if s else "📦 TRONG KHO",
                    "Phòng ban": s.get('department') if s else "Hạ tầng IT",
                    "Chi nhánh": s.get('branch') if s else "Trung tâm",
                    "Thiết bị": [],
                    "Phần mềm": set(), # Dùng set để tránh trùng lặp phần mềm nếu 1 người có nhiều máy cài cùng 1 app
                    "Số lượng": 0
                }
            
            # Xử lý tên thiết bị
            t_name = display_type_map.get(item['type'], "Khác")
            grouped[owner_key]["Thiết bị"].append(f"{item['asset_tag']} ({t_name})")
            
            # Xử lý danh sách phần mềm (Lấy từ cột software_list của asset)
            asset_sw = item.get('software_list') or []
            if asset_sw:
                grouped[owner_key]["Phần mềm"].update(asset_sw)
            
            grouped[owner_key]["Số lượng"] += 1

        # Chuyển đổi dữ liệu để hiển thị
        df_final = pd.DataFrame(list(grouped.values()))
        df_final["Thiết bị"] = df_final["Thiết b"].apply(lambda x: " | ".join(x))
        # Chuyển set phần mềm thành chuỗi, nếu trống thì để "---"
        df_final["Phần mềm"] = df_final["Phần mềm"].apply(lambda x: ", ".join(x) if x else "---")

        if v_filter != "Tất cả":
            df_final = df_final[df_final['Chi nhánh'] == v_filter]

        st.data_editor(
            df_final,
            column_config={
                "Mã NV": st.column_config.TextColumn("ID", width="small"),
                "Nhân viên": st.column_config.TextColumn("👤 Người sở hữu", width="medium"),
                "Thiết bị": st.column_config.TextColumn("🖥️ Danh sách tài sản", width="large"),
                "Phần mềm": st.column_config.TextColumn("📜 Phần mềm/License", width="medium"),
                "Số lượng": st.column_config.NumberColumn("🔢 SL", width="small")
            },
            use_container_width=True, hide_index=True, key="main_grid"
        )

        # Dashboard mini (Giữ nguyên)
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng thiết bị", len(res_all.data))
        c2.metric("Đang cấp phát", sum(df_final[df_final['Mã NV'] != "---"]['Số lượng']))
        c3.metric("Nhân sự nắm giữ", len(df_final[df_final['Mã NV'] != "---"]))
