import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH MAPPING & PHONG CÁCH ---
    type_mapping = {
        "Laptop": "LT", "Desktop PC": "PC", "Monitor": "MN", "Server": "SV", "Khác": "OT"
    }
    # Mapping hậu tố theo 5 chi nhánh chuẩn của bạn
    branch_map = {
        "Miền Bắc": "MB", 
        "Chi nhánh TPHCM": "HCM", 
        "Nhà máy LA": "LA", 
        "Polypack": "PP", 
        "Đà Nẵng": "DN"
    }

    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: #ffffff; border-radius: 18px; padding: 20px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); margin-bottom: 20px;
        }
        .badge-vung { background: #1d1d1f; color: white; padding: 2px 8px; border-radius: 5px; font-size: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700;">📦 Quản trị Tài sản & Điều phối</h1>', unsafe_allow_html=True)

    # --- 2. BỘ LỌC THÔNG MINH THEO VÙNG (PRO FEATURE) ---
    st.markdown("### 🔍 Tra cứu nhanh theo vùng")
    vung_filter = st.segmented_control(
        "Chọn khu vực để xem danh sách:", 
        options=["Tất cả"] + list(branch_map.keys()), 
        default="Tất cả"
    )

    # --- 3. NHẬP KHO TÙY CHỈNH TAG (FIX LỖI 23514) ---
    with st.expander("📥 Nhập thiết bị mới (Tự động tạo Tag theo vùng)", expanded=False):
        with st.form("pro_add_asset_v3", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 2])
            
            raw_id = c1.text_input("Số máy", placeholder="VD: 0001")
            area = c2.selectbox("Chi nhánh quản lý", list(branch_map.keys()))
            label = c3.selectbox("Phân loại", list(type_mapping.keys()))
            
            # Logic tạo Tag: VD PC0001-MB
            full_tag = f"{type_mapping[label]}{raw_id.strip().upper()}-{branch_map[area]}"
            st.info(f"Mã định danh sẽ lưu: **{full_tag}**")
            
            specs = st.text_input("Cấu hình tóm tắt (CPU, RAM...)")

            if st.form_submit_button("🔥 Xác nhận nhập kho"):
                if raw_id:
                    try:
                        # Gửi 'PC' thay vì 'Desktop PC' để vượt qua constraint
                        supabase.table("assets").insert({
                            "asset_tag": full_tag,
                            "type": type_mapping[label], 
                            "status": "Trong kho",
                            "specs": {"note": specs, "area": area}
                        }).execute()
                        st.toast(f"Đã nhập kho {full_tag} thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi DB (Check Constraint): {e}")

    # --- 4. HIỂN THỊ DANH SÁCH TÀI SẢN THEO LỌC ---
    st.markdown(f"#### Danh sách tài sản: {vung_filter}")
    query = supabase.table("assets").select("*")
    if vung_filter != "Tất cả":
        # Lọc những tag có chứa hậu tố vùng (VD: %-MB)
        query = query.ilike("asset_tag", f"%-{branch_map[vung_filter]}")
    
    assets_data = query.execute()
    
    if assets_data.data:
        df = pd.DataFrame(assets_data.data)
        # Hiển thị bảng đẹp hơn
        st.dataframe(df[['asset_tag', 'type', 'status', 'assigned_to_code']], use_container_width=True)
    else:
        st.caption("Chưa có thiết bị nào ở khu vực này.")

    # --- 5. QUẢN LÝ NHÂN SỰ & CẤP PHÁT ---
    st.markdown("---")
    st.markdown("### 👤 Cấp phát cho Nhân viên")
    e_code = st.text_input("Mã nhân viên (Employee Code)", placeholder="VD: 10438").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge-vung">{staff.get('branch')}</span>
                    <h2 style="margin: 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">📂 Phòng ban: {staff.get('department')}</p>
                </div>
            """, unsafe_allow_html=True)
            
            # Logic bàn giao thiết bị
            avail = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
            if avail.data:
                with st.form("assign_form"):
                    choices = {f"{a['asset_tag']} ({a['type']})": a for a in avail.data}
                    pick = st.selectbox("Chọn máy trống để bàn giao", list(choices.keys()))
                    if st.form_submit_button("Xác nhận Bàn giao"):
                        target = choices[pick]
                        supabase.table("assets").update({
                            "assigned_to_code": e_code, "status": "Đang sử dụng"
                        }).eq("id", target['id']).execute()
                        st.success(f"Đã giao {target['asset_tag']} cho {staff['full_name']}")
                        st.rerun()
        else:
            st.warning(f"Chưa có nhân sự mã {e_code}")
            # Form tạo nhân sự mới (giữ nguyên chuẩn 5 chi nhánh)
            with st.expander("🆕 Đăng ký nhân sự mới", expanded=True):
                with st.form("new_staff_pro"):
                    name = st.text_input("Họ và Tên")
                    c_dept, c_branch = st.columns(2)
                    dept = c_dept.selectbox("Phòng ban", ["Kỹ thuật", "Văn phòng", "Sản xuất", "Kế toán"])
                    branch = c_branch.selectbox("Chi nhánh công tác", list(branch_map.keys()))
                    
                    if st.form_submit_button("Lưu hồ sơ"):
                        supabase.table("staff").insert({
                            "employee_code": e_code, "full_name": name,
                            "department": dept, "branch": branch
                        }).execute()
                        st.rerun()
