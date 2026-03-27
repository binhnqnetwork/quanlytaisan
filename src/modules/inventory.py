import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH HỆ THỐNG & STYLE ---
    type_mapping = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}
    status_list = ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý", "Đã thanh lý"]

    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: white; border-radius: 16px; padding: 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #d2d2d7;
            margin-bottom: 20px;
        }
        h1, h2, h3 { color: #1d1d1f; font-weight: 600; }
        .stButton>button {
            border-radius: 12px; background-color: #0071e3; color: white;
            border: none; padding: 8px 20px; transition: 0.3s;
        }
        .stButton>button:hover { background-color: #0077ed; transform: scale(1.02); }
        </style>
    """, unsafe_allow_html=True)

    st.title("📦 Asset Management Professional")
    st.markdown("### Quản trị Tài sản & Điều phối Cấp phát")

    # --- 2. TÌM KIẾM & ĐIỀU PHỐI (APPLE UI) ---
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    c_search, c_status = st.columns([2, 1])
    with c_search:
        e_code = st.text_input("Mã nhân viên", placeholder="Nhập mã nhân viên để điều phối (VD: 10438)").strip().upper()
    
    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            # TRƯỜNG HỢP 1: NHÂN VIÊN ĐÃ TỒN TẠI
            staff = res_staff.data[0]
            with c_status:
                st.success(f"Xác thực: {staff['full_name']}")
            st.markdown(f"📂 **Phòng ban:** {staff.get('department')} | 📍 **Chi nhánh:** {staff.get('branch')}")
            st.markdown('</div>', unsafe_allow_html=True)

            tab_hw, tab_sw = st.tabs(["💻 Bàn giao Thiết bị", "📜 Cấp phát Bản quyền"])
            
            with tab_hw:
                avail = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("assign_hw"):
                        options = {f"{a['asset_tag']} ({a['type'].upper()})": a for a in avail.data}
                        pick = st.selectbox("Chọn máy trong kho để bàn giao", list(options.keys()))
                        if st.form_submit_button("Xác nhận Bàn giao"):
                            asset = options[pick]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", asset['id']).execute()
                            st.toast(f"Đã giao {asset['asset_tag']} cho {staff['full_name']}!", icon="✅")
                            st.rerun()
                else:
                    st.info("Hiện không có thiết bị trống trong kho.")

            with tab_sw:
                my_assets = supabase.table("assets").select("id, asset_tag, software_list").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                    if res_lic.data:
                        with st.form("assign_sw"):
                            target_tag = st.selectbox("Cài lên máy của nhân viên", [a['asset_tag'] for a in my_assets.data])
                            lic_display = [f"{l['name']} (Còn {(l['total_quantity'] or 0) - (l['used_quantity'] or 0)})" for l in res_lic.data]
                            sw_pick_full = st.selectbox("Chọn bản quyền phần mềm", lic_display)
                            
                            if st.form_submit_button("Kích hoạt License"):
                                sw_name = sw_pick_full.split(" (")[0]
                                asset_item = [a for a in my_assets.data if a['asset_tag'] == target_tag][0]
                                current_sw = asset_item.get('software_list') or []
                                
                                if sw_name not in current_sw:
                                    current_sw.append(sw_name)
                                    supabase.table("assets").update({"software_list": current_sw}).eq("id", asset_item['id']).execute()
                                    target_lic = [l for l in res_lic.data if l['name'] == sw_name][0]
                                    supabase.table("licenses").update({
                                        "used_quantity": (target_lic['used_quantity'] or 0) + 1
                                    }).eq("id", target_lic['id']).execute()
                                    st.toast(f"Đã kích hoạt {sw_name}!", icon="🚀")
                                    st.rerun()
                                else:
                                    st.warning("Phần mềm này đã có trên thiết bị.")
                    else:
                        st.info("Không có dữ liệu bản quyền.")
                else:
                    st.warning("Nhân viên này hiện chưa sở hữu máy nào.")
        else:
            # TRƯỜNG HỢP 2: TẠO NHÂN VIÊN MỚI
            st.markdown('</div>', unsafe_allow_html=True)
            st.error(f"Mã nhân viên **{e_code}** chưa có trong hệ thống.")
            with st.expander(f"🆕 Tạo hồ sơ nhân viên mới cho mã {e_code}", expanded=True):
                with st.form("new_staff"):
                    new_name = st.text_input("Họ và tên nhân viên")
                    c1, c2 = st.columns(2)
                    # SỬA ĐỔI TẠI ĐÂY: Dùng text_input thay vì selectbox cho Phòng ban
                    new_dept = c1.text_input("Phòng ban", placeholder="VD: Kế toán, Sản xuất, IT...")
                    new_branch = c2.selectbox("Chi nhánh", list(branch_map.keys()))
                    if st.form_submit_button("Lưu hồ sơ"):
                        if new_name and new_dept:
                            supabase.table("staff").insert({
                                "employee_code": e_code, "full_name": new_name,
                                "department": new_dept, "branch": new_branch
                            }).execute()
                            st.rerun()
                        else:
                            st.error("Vui lòng nhập đầy đủ Tên và Phòng ban.")
    else:
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. NHẬP KHO THIẾT BỊ MỚI ---
    st.markdown("---")
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_asset"):
            c1, c2, c3 = st.columns(3)
            raw_id = c1.text_input("Số máy (VD: 0001)")
            area = c2.selectbox("Chi nhánh quản lý", list(branch_map.keys()))
            label = c3.selectbox("Loại thiết bị", list(type_mapping.keys()))
            tag_preview = f"{type_mapping[label].upper()}{raw_id.strip().upper()}-{branch_map[area]}"
            st.info(f"Mã định danh dự kiến: **{tag_preview}**")
            specs = st.text_area("Cấu hình tóm tắt")
            if st.form_submit_button("Xác nhận Nhập kho"):
                if raw_id:
                    supabase.table("assets").insert({
                        "asset_tag": tag_preview, "type": type_mapping[label],
                        "status": "Trong kho", "specs": {"note": specs}
                    }).execute()
                    st.rerun()

    # --- 4. HỆ THỐNG DANH MỤC TỔNG (ENTERPRISE GRID) ---
    st.markdown("---")
    st.markdown("### 📋 Danh mục Tài sản Chi tiết")
    
    vung_filter = st.segmented_control(
        "Lọc nhanh theo vùng:", 
        ["Tất cả"] + list(branch_map.keys()), 
        default="Tất cả"
    )

    with st.spinner("Đang đồng bộ dữ liệu..."):
        res_all = supabase.table("assets").select("*, staff!assets_assigned_to_code_fkey(full_name, department, branch)").order("asset_tag").execute()
        
    if res_all.data:
        processed_data = []
        for item in res_all.data:
            s_info = item.get('staff')
            processed_data.append({
                "id": item['id'],
                "asset_tag": item['asset_tag'],
                "type": item['type'],
                "status": item['status'],
                "full_name": s_info.get('full_name') if s_info else "📦 Trong kho",
                "department": s_info.get('department') if s_info else "Hạ tầng",
                "branch_name": s_info.get('branch') if s_info else "Trung tâm",
                "software": ", ".join(item.get('software_list', [])) if item.get('software_list') else "---"
            })
        
        df_final = pd.DataFrame(processed_data)

        if vung_filter != "Tất cả":
            suffix = branch_map[vung_filter]
            df_final = df_final[df_final['asset_tag'].str.contains(f"-{suffix}")]

        edited_df = st.data_editor(
            df_final,
            column_config={
                "id": None,
                "asset_tag": st.column_config.TextColumn("🔖 Mã máy", disabled=True),
                "type": st.column_config.TextColumn("🖥️ Loại", disabled=True),
                "status": st.column_config.SelectboxColumn("📊 Trạng thái", options=status_list),
                "full_name": st.column_config.TextColumn("👤 Người sở hữu", disabled=True),
                "department": st.column_config.TextColumn("🏢 Phòng ban", disabled=True),
                "branch_name": st.column_config.TextColumn("📍 Chi nhánh", disabled=True),
                "software": st.column_config.TextColumn("📜 License", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="main_inventory_grid"
        )

        if st.button("💾 Lưu thay đổi trạng thái từ bảng"):
            diff = edited_df[edited_df['status'] != df_final['status']]
            if not diff.empty:
                for _, row in diff.iterrows():
                    supabase.table("assets").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success(f"Đã cập nhật {len(diff)} bản ghi!")
                st.rerun()

        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng thiết bị", len(df_final))
        c2.metric("Đang sử dụng", len(df_final[df_final['status'] == "Đang sử dụng"]))
        c3.metric("Sẵn sàng", len(df_final[df_final['status'] == "Trong kho"]))
