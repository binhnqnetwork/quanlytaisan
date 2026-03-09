import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. STYLE & UI CHUẨN APPLE ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: #ffffff; border-radius: 18px; padding: 24px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
        }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .badge-blue { background: #e8f2ff; color: #0066cc; }
        .badge-green { background: #e2fbe7; color: #1a7f37; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700; color: #1d1d1f; letter-spacing: -0.5px;">📦 Hệ thống Quản trị Tài sản</h1>', unsafe_allow_html=True)

    # --- 2. THỐNG KÊ NHANH (KPIs) ---
    try:
        c1, c2, c3 = st.columns(3)
        # Lấy số lượng thực tế từ DB
        in_stock = supabase.table("assets").select("id", count="exact").eq("status", "Trong kho").execute().count
        deployed = supabase.table("assets").select("id", count="exact").eq("status", "Đang sử dụng").execute().count
        lic_count = supabase.table("licenses").select("id").execute()
        
        c1.metric("Sẵn có trong kho", f"{in_stock or 0} Máy")
        c2.metric("Đang cấp phát", f"{deployed or 0} Máy")
        c3.metric("Danh mục bản quyền", f"{len(lic_count.data) if lic_count.data else 0} bản")
    except Exception:
        st.warning("⚠️ Đang làm mới dữ liệu từ Cloud...")

    # --- 3. NHẬP KHO THIẾT BỊ MỚI (FIX LỖI CONSTRAINT) ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 3])
            new_tag = col1.text_input("Asset Tag", placeholder="VD: PC0001")
            
            # Mapping chuẩn để khớp với Database Constraint "assets_type_check"
            type_map = {
                "Laptop": "LT", 
                "Desktop PC": "PC", 
                "Monitor": "MN", 
                "Server": "SV", 
                "Khác": "OT"
            }
            selected_label = col2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = col3.text_input("Cấu hình tóm tắt (CPU, RAM, SSD...)")
            
            if st.form_submit_button("Xác nhận Nhập kho"):
                if new_tag:
                    try:
                        # Gửi mã (LT, PC...) vào DB thay vì chữ đầy đủ
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": type_map[selected_label], 
                            "status": "Trong kho",
                            "specs": {"note": new_specs}
                        }).execute()
                        st.success(f"Đã nhập kho thiết bị {new_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi nhập liệu: {e}")
                else:
                    st.error("Vui lòng nhập Asset Tag!")

    # --- 4. TRA CỨU & QUẢN LÝ NHÂN SỰ ---
    st.markdown("### 👤 Quản lý theo Nhân sự")
    e_code = st.text_input("Mã nhân viên (Employee Code)", placeholder="Nhập mã để kiểm tra tài sản hoặc đăng ký mới...").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        # TRƯỜNG HỢP 1: NHÂN VIÊN ĐÃ CÓ TRÊN HỆ THỐNG
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge badge-blue">Thành viên hệ thống</span>
                    <h2 style="margin: 10px 0 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">📍 {staff.get('department', 'N/A')} | {staff.get('branch', 'N/A')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col_l, col_r = st.columns(2, gap="large")
            
            with col_l:
                st.markdown("#### 📤 Bàn giao thiết bị")
                avail = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("assign_asset"):
                        asset_options = {f"{a['asset_tag']} ({a['type']})": a for a in avail.data}
                        choice = st.selectbox("Chọn thiết bị trống", list(asset_options.keys()))
                        if st.form_submit_button("Xác nhận cấp phát"):
                            target = asset_options[choice]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", target['id']).execute()
                            st.toast(f"Đã bàn giao cho {staff['full_name']}")
                            st.rerun()
                else:
                    st.info("Hiện không còn máy trống trong kho.")

            with col_r:
                st.markdown("#### 🖥️ Thiết bị đang giữ")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            st.write(f"**{a['asset_tag']}** - {a['type']}")
                            if st.button("Thu hồi", key=f"ret_{a['id']}", use_container_width=True):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("id", a['id']).execute()
                                st.rerun()
                else:
                    st.caption("Nhân viên này chưa giữ thiết bị nào.")

        # TRƯỜNG HỢP 2: ĐĂNG KÝ NHÂN VIÊN MỚI
        else:
            st.warning(f"Mã nhân viên **{e_code}** chưa tồn tại.")
            with st.expander(f"🆕 Tạo hồ sơ nhân sự mới: {e_code}", expanded=True):
                with st.form("new_staff_form"):
                    new_name = st.text_input("Họ và Tên")
                    
                    c1, c2 = st.columns(2)
                    # Phòng ban: Chọn hoặc Nhập tay
                    dept_opts = ["Nhân viên VP", "Kỹ thuật", "Kế toán", "Kinh doanh", "Sản xuất", "Khác (Nhập tay)"]
                    dept_choice = c1.selectbox("Phòng ban", dept_opts)
                    if dept_choice == "Khác (Nhập tay)":
                        final_dept = c1.text_input("Tên phòng ban cụ thể", placeholder="VD: Marketing...")
                    else:
                        final_dept = dept_choice

                    # Chi nhánh: 5 vị trí theo yêu cầu
                    branch_list = ["Polypack", "Nhà máy LA", "Chi nhánh TPHCM", "Đà Nẵng", "Miền Bắc"]
                    new_branch = c2.selectbox("Chi nhánh", branch_list)
                    
                    if st.form_submit_button("Lưu hồ sơ & Tiếp tục"):
                        if new_name and final_dept:
                            try:
                                supabase.table("staff").insert({
                                    "employee_code": e_code,
                                    "full_name": new_name,
                                    "department": final_dept,
                                    "branch": new_branch
                                }).execute()
                                st.success("Đã đăng ký nhân sự mới!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi DB: {e}")
                        else:
                            st.error("Vui lòng nhập đầy đủ thông tin nhân viên.")

    # --- 5. LỊCH SỬ VẬN HÀNH ---
    st.markdown("---")
    st.markdown("### 🛠️ Nhật ký bảo trì gần đây")
    recent_logs = supabase.table("maintenance_log").select("*, assets(asset_tag)").order("performed_at", desc=True).limit(5).execute()
    if recent_logs.data:
        for log in recent_logs.data:
            with st.expander(f"📌 {log['assets']['asset_tag']} | {log['action_type']} - {log['performed_at']}"):
                st.write(log['description'])
