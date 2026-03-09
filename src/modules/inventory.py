import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    st.title("👤 Quản lý Cấp phát & Kho thiết bị")

    # --- PHẦN 1: NHẬP THIẾT BỊ MỚI VÀO KHO ---
    # Mục đích: Tạo ra các Asset Tag trống (chưa có người giữ) để dùng cho phần Cấp phát
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_to_stock"):
            st.write("Điền thông tin thiết bị mới để nhập vào kho hệ thống")
            c1, c2, c3 = st.columns([2, 2, 2])
            new_tag = c1.text_input("Mã tài sản (Tag)", placeholder="VD: PC001, LAP05...").strip().upper()
            new_type = c2.selectbox("Loại thiết bị", ["Laptop", "PC Desktop", "Monitor", "Printer", "Other"])
            # Gợi ý cấu hình nhanh (Lưu vào cột specs JSONB nếu cần)
            new_specs = c3.text_input("Ghi chú cấu hình", placeholder="VD: Core i5, 16GB RAM")
            
            if st.form_submit_button("💾 Lưu vào kho"):
                if new_tag:
                    # Kiểm tra trùng mã tag trước khi insert
                    check_exist = supabase.table("assets").select("asset_tag").eq("asset_tag", new_tag).execute()
                    if check_exist.data:
                        st.error(f"Mã {new_tag} đã tồn tại trong hệ thống!")
                    else:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag,
                            "type": new_type,
                            "status": "Trong kho",
                            "specs": {"note": new_specs} if new_specs else {},
                            "assigned_to_code": None # Quan trọng: Để trống để hiện ở danh sách cấp phát
                        }).execute()
                        st.success(f"Đã nhập {new_tag} vào kho thành công.")
                        st.rerun()
                else:
                    st.warning("Vui lòng nhập Mã tài sản.")

    st.divider()

    # --- PHẦN 2: QUẢN LÝ NHÂN SỰ & CẤP PHÁT ---
    loc_map = {"Nhà máy Long An": 1, "TP.HCM": 2, "Đà Nẵng": 3, "Miền Bắc": 4, "Polypack": 5}
    branch_list = list(loc_map.keys())

    # Bước 2.1: Nhận diện nhân sự
    e_code = st.text_input("🔍 Tra cứu Mã nhân viên", placeholder="VD: NV001").strip().upper()
    st_data = {"full_name": "", "department": "", "branch": "Nhà máy Long An", "is_active": True}
    exists = False

    if e_code:
        res = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        if res.data:
            st_data = res.data[0]
            exists = True
            st.success(f"👤 Nhân viên: **{st_data['full_name']}** | Bộ phận: **{st_data['department']}**")
        else:
            st.warning("Mã nhân viên mới. Vui lòng cập nhật hồ sơ bên dưới.")

    # Form quản lý hồ sơ nhân sự
    with st.expander("📝 Cập nhật hồ sơ nhân viên", expanded=not exists if e_code else False):
        with st.form("staff_form_v11"):
            c1, c2, c3 = st.columns(3)
            f_name = c1.text_input("Họ và Tên", value=st_data.get("full_name", ""))
            f_dept = c2.text_input("Phòng ban", value=st_data.get("department", ""))
            db_branch = st_data.get("branch", "Nhà máy Long An")
            d_idx = branch_list.index(db_branch) if db_branch in branch_list else 0
            f_branch = c3.selectbox("Chi nhánh", branch_list, index=d_idx)
            
            if st.form_submit_button("💾 Xác nhận hồ sơ"):
                if e_code and f_name:
                    supabase.table("staff").upsert({
                        "employee_code": e_code, 
                        "full_name": f_name, 
                        "department": f_dept, 
                        "branch": f_branch,
                        "location_id": loc_map.get(f_branch),
                        "is_active": True
                    }, on_conflict="employee_code").execute()
                    st.success("Đã cập nhật hồ sơ nhân sự!")
                    st.rerun()

    if exists:
        # Bước 2.2: Cấp phát tài sản từ kho & Thu hồi
        st.divider()
        col_assign, col_holding = st.columns([1, 1])
        
        with col_assign:
            st.subheader("📦 Cấp tài sản mới")
            # Chỉ lấy thiết bị 'Trong kho' và 'Chưa gán'
            available_res = supabase.table("assets").select("asset_tag, type")\
                .or_("assigned_to_code.is.null,assigned_to_code.eq.''")\
                .eq("status", "Trong kho")\
                .neq("type", "Server")\
                .execute()
            
            if available_res.data:
                options = {f"{item['asset_tag']} ({item['type']})": item['asset_tag'] for item in available_res.data}
                with st.form("assign_asset_form"):
                    selected_display = st.selectbox("Chọn thiết bị từ kho", options.keys())
                    target_tag = options[selected_display]
                    a_date = st.date_input("Ngày bàn giao tài sản")
                    
                    if st.form_submit_button("🚀 Xác nhận bàn giao"):
                        supabase.table("assets").update({
                            "assigned_to_code": e_code,
                            "purchase_date": str(a_date),
                            "status": "Đang sử dụng"
                        }).eq("asset_tag", target_tag).execute()
                        st.success(f"Đã gán {target_tag} cho {st_data['full_name']}")
                        st.rerun()
            else:
                st.info("💡 Kho hiện không còn máy trống. Hãy dùng mục 'Nhập thiết bị mới' ở trên.")

        with col_holding:
            st.subheader("🖥️ Thiết bị đang giữ")
            as_res = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
            if as_res.data:
                for a in as_res.data:
                    with st.container(border=True):
                        st.write(f"**{a['asset_tag']}** - {a['type']}")
                        st.caption(f"📅 Ngày gán: {a.get('purchase_date', 'N/A')}")
                        if st.button(f"🔄 Thu hồi {a['asset_tag']}", key=f"ret_{a['asset_tag']}"):
                            supabase.table("assets").update({
                                "assigned_to_code": None, 
                                "status": "Trong kho"
                            }).eq("asset_tag", a['asset_tag']).execute()
                            st.rerun()
            else:
                st.write("*(Nhân viên này chưa nắm giữ thiết bị)*")

        # Bước 2.3: Nhật ký Bảo trì
        st.divider()
        st.subheader("🛠️ Nhật ký Bảo trì cho Nhân sự này")
        my_assets = {a['asset_tag']: a['id'] for a in as_res.data} if as_res.data else {}
        
        if my_assets:
            with st.form("maintenance_form_v11"):
                c1, c2 = st.columns(2)
                m_tag = c1.selectbox("Máy cần bảo trì", list(my_assets.keys()))
                m_type = c2.selectbox("Loại tác động", ["Bảo trì định kỳ", "Sửa chữa hỏng hóc", "Thay linh kiện", "Nâng cấp cấu hình"])
                m_desc = st.text_area("Chi tiết xử lý", placeholder="VD: Thay ổ cứng SSD 256GB...")
                m_date = st.date_input("Ngày thực hiện")
                
                if st.form_submit_button("💾 Lưu Nhật ký"):
                    supabase.table("maintenance_log").insert({
                        "asset_id": my_assets[m_tag],
                        "action_type": m_type,
                        "description": m_desc,
                        "performed_at": str(m_date)
                    }).execute()
                    
                    supabase.table("assets").update({"last_maintenance": str(m_date)}).eq("id", my_assets[m_tag]).execute()
                    st.success(f"Đã lưu lịch sử cho {m_tag}")
                    st.rerun()
            
            # Hiển thị lịch sử bảo trì gần đây của các thiết bị nhân sự này đang giữ
            log_res = supabase.table("maintenance_log").select("*").in_("asset_id", list(my_assets.values())).order("performed_at", desc=True).execute()
            if log_res.data:
                st.dataframe(pd.DataFrame(log_res.data)[['performed_at', 'action_type', 'description']], 
                             use_container_width=True, hide_index=True)
        else:
            st.info("Nhân viên này chưa có thiết bị để thực hiện bảo trì.")
