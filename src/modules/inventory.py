import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- STYLE CHUẨN APPLE (GLASSMORPHISM & MINIMAL) ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .main-header { font-family: 'SF Pro Display', sans-serif; font-weight: 600; color: #1d1d1f; letter-spacing: -0.5px; }
        .card-container { background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin-bottom: 20px; border: 1px solid #d2d2d7; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">Inventory System</h1>', unsafe_allow_html=True)

    # --- TOP ACTIONS: NHẬP KHO (QUY TRÌNH TINH GỌN) ---
    with st.expander("＋ Nhập thiết bị mới", expanded=False):
        with st.form("apple_add_stock", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            new_tag = c1.text_input("Asset Tag", placeholder="e.g. MBP-001")
            
            # Mapping chuẩn hóa Database để tránh lỗi constraint
            type_map = {
                "MacBook / Laptop": "laptop",
                "iMac / PC Desktop": "pc",
                "Studio Display / Monitor": "monitor",
                "Printer": "printer",
                "Network Device": "network",
                "Other Accessories": "other"
            }
            selected_type = c2.selectbox("Category", list(type_map.keys()))
            new_specs = c3.text_input("Technical Specifications", placeholder="M3 Max, 32GB RAM, 1TB SSD")
            
            if st.form_submit_button("Lưu vào kho hệ thống"):
                if new_tag:
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.upper(),
                            "type": type_map[selected_type],
                            "status": "Trong kho",
                            "specs": {"note": new_specs} if new_specs else {},
                            "assigned_to_code": None
                        }).execute()
                        st.toast(f"Đã thêm {new_tag} thành công", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                else:
                    st.warning("Vui lòng nhập Mã tài sản.")

    # --- MAIN FLOW: QUẢN LÝ NHÂN SỰ ---
    st.markdown('<p style="color: #86868b; margin-top: 20px;">TRA CỨU NHÂN SỰ</p>', unsafe_allow_html=True)
    e_code = st.text_input("Employee ID", placeholder="Nhập mã NV...", label_visibility="collapsed").strip().upper()

    if e_code:
        # Lấy dữ liệu nhân viên và thiết bị đồng thời
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="card-container">
                    <span style="color: #0066cc; font-weight: 600;">{staff['employee_code']}</span>
                    <h2 style="margin: 0; font-size: 28px;">{staff['full_name']}</h2>
                    <p style="color: #86868b;">{staff['department']} • {staff['branch']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Chia Layout: Cấp phát & Thiết bị hiện có
            col1, col2 = st.columns([1, 1], gap="large")
            
            with col1:
                st.markdown("### 📦 Cấp phát mới")
                # Lọc bỏ Server và chỉ lấy đồ trong kho
                available = supabase.table("assets").select("asset_tag, type")\
                    .eq("status", "Trong kho")\
                    .neq("type", "server").execute()
                
                if available.data:
                    with st.form("assign_form_pro"):
                        options = {f"{item['asset_tag']} ({item['type']})": item['asset_tag'] for item in available.data}
                        target = st.selectbox("Chọn thiết bị", options.keys())
                        date_assign = st.date_input("Ngày bàn giao")
                        if st.form_submit_button("Xác nhận bàn giao"):
                            supabase.table("assets").update({
                                "assigned_to_code": e_code,
                                "status": "Đang sử dụng",
                                "purchase_date": str(date_assign)
                            }).eq("asset_tag", options[target]).execute()
                            st.rerun()
                else:
                    st.info("Kho hiện tại đã hết thiết bị sẵn sàng.")

            with col2:
                st.markdown("### 🖥️ Thiết bị đang sử dụng")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            c_a, c_b = st.columns([3, 1])
                            c_a.write(f"**{a['asset_tag']}**")
                            c_a.caption(f"{a['type'].capitalize()} | Gán ngày: {a.get('purchase_date', 'N/A')}")
                            if c_b.button("Thu hồi", key=f"ret_{a['asset_tag']}"):
                                supabase.table("assets").update({
                                    "assigned_to_code": None,
                                    "status": "Trong kho"
                                }).eq("asset_tag", a['asset_tag']).execute()
                                st.rerun()
                else:
                    st.write("Chưa có thiết bị được gán.")

            # --- NHẬT KÝ BẢO TRÌ (DẠNG TIMELINE) ---
            st.markdown("---")
            st.markdown("### 🛠️ Nhật ký bảo trì")
            asset_list = {a['asset_tag']: a['id'] for a in my_assets.data}
            
            if asset_list:
                with st.expander("Ghi chú bảo trì mới"):
                    with st.form("maint_form"):
                        sel_asset = st.selectbox("Thiết bị", list(asset_list.keys()))
                        m_type = st.selectbox("Loại", ["Định kỳ", "Sửa chữa", "Nâng cấp"])
                        m_desc = st.text_area("Nội dung xử lý")
                        if st.form_submit_button("Lưu nhật ký"):
                            supabase.table("maintenance_log").insert({
                                "asset_id": asset_list[sel_asset],
                                "action_type": m_type,
                                "description": m_desc,
                                "performed_at": str(datetime.now().date())
                            }).execute()
                            # Cập nhật ngày bảo trì cuối
                            supabase.table("assets").update({"last_maintenance": str(datetime.now().date())}).eq("id", asset_list[sel_asset]).execute()
                            st.rerun()
                
                # Hiển thị lịch sử tinh gọn
                logs = supabase.table("maintenance_log").select("*").in_("asset_id", list(asset_list.values())).order("performed_at", desc=True).execute()
                if logs.data:
                    st.table(pd.DataFrame(logs.data)[['performed_at', 'action_type', 'description']].head(5))
        
        else:
            # Giao diện tạo mới nhân viên nếu không tìm thấy
            st.info("Không tìm thấy nhân viên. Vui lòng hoàn tất hồ sơ phía dưới để khởi tạo.")
            with st.form("new_staff_pro"):
                c1, c2 = st.columns(2)
                f_name = c1.text_input("Họ và Tên")
                f_dept = c2.text_input("Phòng ban")
                f_branch = st.selectbox("Chi nhánh", ["Nhà máy Long An", "TP.HCM", "Đà Nẵng", "Miền Bắc", "Polypack"])
                if st.form_submit_button("Khởi tạo hồ sơ nhân sự"):
                    if f_name:
                        supabase.table("staff").insert({
                            "employee_code": e_code, "full_name": f_name,
                            "department": f_dept, "branch": f_branch, "is_active": True
                        }).execute()
                        st.rerun()
