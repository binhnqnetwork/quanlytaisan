import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- STYLE CHUẨN APPLE ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            border-radius: 18px;
            padding: 24px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
        }
        .badge { padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
        .badge-blue { background: #e8f2ff; color: #0066cc; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 600;">Inventory System</h1>', unsafe_allow_html=True)

    # --- SECTION 1: NHẬP KHO (VỚI AUTO-VALIDATOR) ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("apple_add_stock", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            new_tag = c1.text_input("Asset Tag", placeholder="VD: PC-001")
            
            type_map = {
                "MacBook / Laptop": "laptop", "iMac / PC Desktop": "pc",
                "Display / Monitor": "monitor", "Server": "server", "Other": "other"
            }
            selected_label = c2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = c3.text_input("Ghi chú cấu hình", placeholder="Core i5, RAM 16GB...")
            
            if st.form_submit_button("Lưu vào kho"):
                if new_tag:
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": type_map[selected_label],
                            "status": "Trong kho",
                            "specs": {"note": new_specs},
                            "assigned_to_code": None
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

    # --- SECTION 2: QUẢN LÝ NHÂN SỰ & CẤP PHÁT ---
    st.markdown("### 👤 Tra cứu nhân sự")
    e_code = st.text_input("Mã nhân viên", placeholder="Nhập ID...", label_visibility="collapsed").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge badge-blue">{staff['employee_code']}</span>
                    <h2 style="margin: 10px 0 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">{staff['department']} • {staff['branch']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col_assign, col_current = st.columns([1, 1], gap="large")
            
            # --- CẤP PHÁT MỚI ---
            with col_assign:
                st.markdown("#### 📦 Bàn giao thiết bị")
                available = supabase.table("assets").select("*").eq("status", "Trong kho").neq("type", "server").execute()
                
                if available.data:
                    with st.form("assign_form"):
                        asset_options = {f"{a['asset_tag']} ({a['type']})": a for a in available.data}
                        target = st.selectbox("Chọn từ kho", list(asset_options.keys()))
                        date_assign = st.date_input("Ngày bàn giao")
                        
                        if st.form_submit_button("Xác nhận bàn giao"):
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng",
                                "purchase_date": str(date_assign)
                            }).eq("asset_tag", asset_options[target]['asset_tag']).execute()
                            st.rerun()
                else:
                    st.info("Kho không còn thiết bị trống.")

            # --- QUẢN LÝ THIẾT BỊ & BẢN QUYỀN (LICENSES) ---
            with col_current:
                st.markdown("#### 🖥️ Thiết bị & Phần mềm")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            st.markdown(f"**{a['asset_tag']}** ({a['type'].upper()})")
                            
                            # Hiển thị License hiện có
                            softwares = a.get('software_list') or []
                            if softwares:
                                st.caption(f"🛡️ Đã cài: {', '.join(softwares)}")
                            else:
                                st.caption("⚪ Chưa cài bản quyền")

                            # Logic gán License mới (Giao diện tích hợp)
                            with st.expander("Gán bản quyền (License)"):
                                lic_res = supabase.table("licenses").select("*").execute()
                                if lic_res.data:
                                    # Lọc các License còn hàng
                                    valid_lics = [l for l in lic_res.data if (l['total_quantity'] - l['used_quantity']) > 0]
                                    if valid_lics:
                                        lic_names = [l['name'] for l in valid_lics]
                                        selected_lic = st.selectbox("Chọn phần mềm", ["-- Chọn --"] + lic_names, key=f"sel_{a['id']}")
                                        
                                        if st.button("Cài đặt & Trừ kho", key=f"btn_{a['id']}") and selected_lic != "-- Chọn --":
                                            # 1. Cập nhật Software List cho Asset
                                            if selected_lic not in softwares:
                                                softwares.append(selected_lic)
                                                supabase.table("assets").update({"software_list": softwares}).eq("id", a['id']).execute()
                                                
                                                # 2. Cập nhật Used Quantity cho License
                                                lic_item = next(l for l in valid_lics if l['name'] == selected_lic)
                                                supabase.table("licenses").update({
                                                    "used_quantity": lic_item['used_quantity'] + 1
                                                }).eq("id", lic_item['id']).execute()
                                                
                                                st.success(f"Đã gán {selected_lic}!")
                                                st.rerun()
                                    else:
                                        st.error("Hết bản quyền trong kho!")

                            if st.button("Thu hồi thiết bị", key=f"ret_{a['asset_tag']}"):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("asset_tag", a['asset_tag']).execute()
                                st.rerun()
                else:
                    st.write("Chưa giữ thiết bị nào.")

            # --- NHẬT KÝ BẢO TRÌ ---
            st.markdown("---")
            st.markdown("### 🛠️ Nhật ký bảo trì")
            asset_dict = {a['asset_tag']: a['id'] for a in my_assets.data}
            if asset_dict:
                with st.expander("Ghi chú bảo trì mới"):
                    with st.form("maint_form"):
                        sel_tag = st.selectbox("Thiết bị", list(asset_dict.keys()))
                        m_type = st.selectbox("Hình thức", ["Bảo trì định kỳ", "Sửa chữa", "Nâng cấp"])
                        m_desc = st.text_area("Nội dung")
                        if st.form_submit_button("Lưu lịch sử"):
                            today = str(datetime.now().date())
                            supabase.table("maintenance_log").insert({
                                "asset_id": asset_dict[sel_tag], "action_type": m_type,
                                "description": m_desc, "performed_at": today
                            }).execute()
                            supabase.table("assets").update({"last_maintenance": today}).eq("id", asset_dict[sel_tag]).execute()
                            st.rerun()
        else:
            st.warning("Mã nhân viên không tồn tại.")
