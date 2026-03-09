import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH HỆ THỐNG & STYLE ---
    type_mapping = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}

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

    st.title("📦 Asset Management")
    st.markdown("### Quản trị Tài sản & Cấp phát")

    # --- 2. TÌM KIẾM NHÂN VIÊN ---
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    c_search, c_status = st.columns([2, 1])
    with c_search:
        e_code = st.text_input("Mã nhân viên", placeholder="Nhập mã nhân viên (VD: 10438)").strip().upper()
    
    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            # --- TRƯỜNG HỢP 1: NHÂN VIÊN ĐÃ TỒN TẠI ---
            staff = res_staff.data[0]
            with c_status:
                st.success(f"Verified: {staff['full_name']}")
            st.markdown(f"📂 **Phòng ban:** {staff.get('department')} | 📍 **Chi nhánh:** {staff.get('branch')}")
            st.markdown('</div>', unsafe_allow_html=True)

            tab_hw, tab_sw = st.tabs(["💻 Bàn giao Thiết bị", "📜 Cấp phát Bản quyền"])
            
            # TAB PHẦN CỨNG
            with tab_hw:
                avail = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("apple_assign_hw"):
                        options = {f"{a['asset_tag']} ({a['type'].upper()})": a for a in avail.data}
                        pick = st.selectbox("Chọn máy trong kho để bàn giao", list(options.keys()))
                        if st.form_submit_button("Xác nhận Bàn giao"):
                            asset = options[pick]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", asset['id']).execute()
                            st.toast(f"Đã giao {asset['asset_tag']} thành công!", icon="✅")
                            st.rerun()
                else:
                    st.info("Hiện không có thiết bị trống trong kho.")

            # TAB PHẦN MỀM (FIX LỖI 'name')
            with tab_sw:
                my_assets = supabase.table("assets").select("id, asset_tag, software_list").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    # Truy vấn bảng licenses theo đúng tên cột thực tế: 'name', 'total_quantity', 'used_quantity'
                    res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                    
                    if res_lic.data:
                        with st.form("apple_assign_sw"):
                            target_tag = st.selectbox("Cài lên máy của nhân viên", [a['asset_tag'] for a in my_assets.data])
                            
                            lic_display = []
                            for l in res_lic.data:
                                remaining = (l['total_quantity'] or 0) - (l['used_quantity'] or 0)
                                lic_display.append(f"{l['name']} (Còn {remaining})")
                            
                            sw_pick_full = st.selectbox("Chọn bản quyền phần mềm", lic_display)
                            
                            if st.form_submit_button("Kích hoạt License"):
                                sw_name = sw_pick_full.split(" (")[0]
                                asset_item = [a for a in my_assets.data if a['asset_tag'] == target_tag][0]
                                
                                # Cập nhật danh sách phần mềm
                                current_sw = asset_item.get('software_list') or []
                                if sw_name not in current_sw:
                                    current_sw.append(sw_name)
                                    supabase.table("assets").update({"software_list": current_sw}).eq("id", asset_item['id']).execute()
                                    
                                    # Trừ số lượng bản quyền
                                    target_lic = [l for l in res_lic.data if l['name'] == sw_name][0]
                                    supabase.table("licenses").update({
                                        "used_quantity": (target_lic['used_quantity'] or 0) + 1
                                    }).eq("id", target_lic['id']).execute()
                                    
                                    st.toast(f"Đã kích hoạt {sw_name}!", icon="🚀")
                                    st.rerun()
                                else:
                                    st.warning("Phần mềm này đã có trên thiết bị.")
                    else:
                        st.info("Không có dữ liệu bản quyền phần mềm.")
                else:
                    st.warning("Nhân viên cần được gán máy trước khi cấp bản quyền.")

        else:
            # --- TRƯỜNG HỢP 2: TẠO NHÂN VIÊN MỚI ---
            st.markdown('</div>', unsafe_allow_html=True)
            st.error(f"Mã nhân viên **{e_code}** chưa có trong hệ thống.")
            with st.expander(f"🆕 Tạo hồ sơ nhân viên mới cho mã {e_code}", expanded=True):
                with st.form("apple_new_staff"):
                    new_name = st.text_input("Họ và tên nhân viên")
                    c1, c2 = st.columns(2)
                    new_dept = c1.selectbox("Phòng ban", ["IT", "Kỹ thuật", "Văn phòng", "Sản xuất", "Kế toán"])
                    new_branch = c2.selectbox("Chi nhánh", list(branch_map.keys()))
                    
                    if st.form_submit_button("Lưu hồ sơ"):
                        if new_name:
                            supabase.table("staff").insert({
                                "employee_code": e_code, "full_name": new_name,
                                "department": new_dept, "branch": new_branch
                            }).execute()
                            st.toast("Đã thêm nhân viên mới!", icon="👤")
                            st.rerun()
                        else:
                            st.error("Vui lòng không để trống tên.")
    else:
        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Nhập mã nhân viên để bắt đầu điều phối tài sản.")

    # --- 3. QUẢN TRỊ NHẬP KHO (DÀNH CHO ADMIN) ---
    st.markdown("---")
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("apple_add_asset"):
            c1, c2, c3 = st.columns(3)
            raw_id = c1.text_input("Số máy (VD: 0001)")
            area = c2.selectbox("Chi nhánh quản lý", list(branch_map.keys()))
            label = c3.selectbox("Loại thiết bị", list(type_mapping.keys()))
            
            tag_preview = f"{type_mapping[label].upper()}{raw_id.strip().upper()}-{branch_map[area]}"
            st.info(f"Mã định danh dự kiến: **{tag_preview}**")
            specs = st.text_area("Cấu hình tóm tắt")
            
            if st.form_submit_button("Xác nhận Nhập kho"):
                if raw_id:
                    try:
                        # Fix lỗi 23514: Gửi 'pc', 'laptop' (viết thường)
                        supabase.table("assets").insert({
                            "asset_tag": tag_preview,
                            "type": type_mapping[label],
                            "status": "Trong kho",
                            "specs": {"note": specs}
                        }).execute()
                        st.toast(f"Đã nhập kho {tag_preview}", icon="📦")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

    # --- 4. DANH MỤC TỔNG QUÁT ---
    st.markdown("### 📋 Danh mục tài sản")
    vung_filter = st.segmented_control("Lọc theo vùng:", ["Tất cả"] + list(branch_map.keys()), default="Tất cả")
    query = supabase.table("assets").select("*")
    if vung_filter != "Tất cả":
        query = query.ilike("asset_tag", f"%-{branch_map[vung_filter]}")
    
    assets_data = query.execute()
    if assets_data.data:
        df = pd.DataFrame(assets_data.data)
        st.dataframe(df[['asset_tag', 'type', 'status', 'assigned_to_code']], use_container_width=True)
