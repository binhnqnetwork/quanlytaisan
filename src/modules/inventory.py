import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. STYLE & UI ---
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
        .badge-green { background: #e2fbe7; color: #1a7f37; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700; color: #1d1d1f;">📦 Hệ thống Quản trị Tài sản</h1>', unsafe_allow_html=True)

    # --- 2. THỐNG KÊ NHANH (KPIs) ---
    try:
        c1, c2, c3 = st.columns(3)
        # Sửa lỗi đơn vị 'TB' thành 'Máy' để logic hơn với phần cứng
        in_stock = supabase.table("assets").select("id", count="exact").eq("status", "Trong kho").execute().count
        deployed = supabase.table("assets").select("id", count="exact").eq("status", "Đang sử dụng").execute().count
        lic_count = supabase.table("licenses").select("id").execute()
        
        c1.metric("Sẵn có trong kho", f"{in_stock or 0} Máy")
        c2.metric("Đang cấp phát", f"{deployed or 0} Máy")
        c3.metric("Danh mục phần mềm", f"{len(lic_count.data) if lic_count.data else 0} bản")
    except Exception:
        st.warning("⚠️ Đang kết nối đến cơ sở dữ liệu...")

    # --- 3. NHẬP KHO THIẾT BỊ MỚI ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("add_asset_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 3])
            new_tag = col1.text_input("Asset Tag", placeholder="VD: PC0001")
            
            # Map chuẩn để tránh lỗi Check Constraint của Database
            type_map = {"Laptop": "LT", "Desktop PC": "PC", "Monitor": "MN", "Server": "SV", "Khác": "OT"}
            selected_label = col2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = col3.text_input("Cấu hình tóm tắt")
            
            if st.form_submit_button("Xác nhận Nhập kho"):
                if new_tag:
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": type_map[selected_label],
                            "status": "Trong kho",
                            "specs": {"note": new_specs}
                        }).execute()
                        st.success(f"Đã nhập kho thiết bị {new_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    # --- 4. TRA CỨU & QUẢN LÝ NHÂN SỰ (AUTO-REGISTER) ---
    st.markdown("### 👤 Quản lý theo Nhân sự")
    e_code = st.text_input("Nhập Mã nhân viên (Employee Code)", placeholder="Nhập mã để tra cứu hoặc đăng ký mới...").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        # TRƯỜNG HỢP 1: NHÂN VIÊN ĐÃ TỒN TẠI
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge badge-blue">Thành viên hệ thống</span>
                    <h2 style="margin: 10px 0 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">📍 {staff.get('department', 'N/A')} | {staff.get('branch', 'N/A')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Chia cột thao tác
            col_left, col_right = st.columns(2, gap="large")
            
            with col_left:
                st.markdown("#### 📤 Bàn giao thiết bị")
                avail = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("assign_asset"):
                        asset_list = {f"{a['asset_tag']} - {a['type']}": a for a in avail.data}
                        choice = st.selectbox("Chọn máy trống", list(asset_list.keys()))
                        if st.form_submit_button("Xác nhận cấp phát"):
                            target = asset_list[choice]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", target['id']).execute()
                            st.toast(f"Đã cấp máy cho {staff['full_name']}")
                            st.rerun()
                else:
                    st.info("Kho hết máy trống.")

            with col_right:
                st.markdown("#### 🖥️ Thiết bị đang giữ")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            st.write(f"**{a['asset_tag']}**")
                            if st.button("Thu hồi", key=f"ret_{a['id']}"):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("id", a['id']).execute()
                                st.rerun()
                else:
                    st.caption("Chưa giữ máy nào.")

        # TRƯỜNG HỢP 2: NHÂN VIÊN MỚI (CHƯA TỒN TẠI)
        else:
            st.warning(f"Mã nhân viên **{e_code}** chưa có trên hệ thống.")
            with st.expander(f"🆕 Đăng ký nhân sự mới với mã {e_code}", expanded=True):
                with st.form("new_staff_form"):
                    new_name = st.text_input("Họ và Tên")
                    c_s1, c_s2 = st.columns(2)
                    new_dept = c_s1.selectbox("Bộ phận", ["Kỹ thuật", "Kế toán", "Kinh doanh", "Nhân sự", "Sản xuất"])
                    new_branch = c_s2.selectbox("Chi nhánh", ["Hồ Chí Minh", "Hà Nội", "Đà Nẵng"])
                    
                    if st.form_submit_button("Tạo hồ sơ & Tiếp tục"):
                        if new_name:
                            try:
                                supabase.table("staff").insert({
                                    "employee_code": e_code,
                                    "full_name": new_name,
                                    "department": new_dept,
                                    "branch": new_branch
                                }).execute()
                                st.success("Đã tạo nhân sự mới thành công!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Không thể tạo hồ sơ: {e}")
                        else:
                            st.error("Vui lòng nhập tên nhân viên.")

    # --- 5. LỊCH SỬ BẢO TRÌ (MỞ RỘNG) ---
    st.markdown("---")
    st.markdown("### 🛠️ Nhật ký vận hành toàn hệ thống")
    # Hiển thị 5 bản ghi bảo trì gần nhất
    recent_m = supabase.table("maintenance_log").select("*, assets(asset_tag)").order("performed_at", desc=True).limit(5).execute()
    if recent_m.data:
        for m in recent_m.data:
            with st.expander(f"📌 {m['assets']['asset_tag']} - {m['action_type']} ({m['performed_at']})"):
                st.write(f"**Nội dung:** {m['description']}")
