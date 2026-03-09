import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- STYLE CHUẨN APPLE & ĐỊNH DẠNG BẢNG ---
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
        .badge-green { background: #e2fbe7; color: #1a7f37; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 600; color: #1d1d1f;">Inventory System</h1>', unsafe_allow_html=True)

    # --- THỐNG KÊ NHANH (KPIs) ---
    all_assets = supabase.table("assets").select("status", count="exact").execute()
    if all_assets.count is not None:
        c1, c2, c3 = st.columns(3)
        with c1:
            in_stock = supabase.table("assets").select("id", count="exact").eq("status", "Trong kho").execute().count
            st.metric("📦 Thiết bị sẵn có", in_stock)
        with c2:
            deployed = supabase.table("assets").select("id", count="exact").eq("status", "Đang sử dụng").execute().count
            st.metric("🖥️ Đang cấp phát", deployed)
        with c3:
            # Lấy số license sắp hết từ bảng licenses
            low_lic = supabase.table("licenses").select("id").execute()
            st.metric("🔑 Loại bản quyền", len(low_lic.data) if low_lic.data else 0)

    # --- SECTION 1: NHẬP KHO THIẾT BỊ ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("apple_add_stock", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            new_tag = c1.text_input("Asset Tag", placeholder="VD: PC-2026-001")
            
            type_map = {
                "MacBook / Laptop": "laptop", "iMac / PC Desktop": "pc",
                "Display / Monitor": "monitor", "Server": "server", "Other": "other"
            }
            selected_label = c2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = c3.text_input("Ghi chú cấu hình", placeholder="M3 Chip, 16GB RAM...")
            
            if st.form_submit_button("Lưu vào hệ thống"):
                if new_tag:
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": type_map[selected_label],
                            "status": "Trong kho",
                            "specs": {"note": new_specs},
                            "assigned_to_code": None,
                            "software_list": [] # Khởi tạo mảng trống
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

    # --- SECTION 2: TRA CỨU NHÂN SỰ & QUẢN LÝ CẤP PHÁT ---
    st.markdown("### 👤 Quản lý theo Nhân sự")
    e_code = st.text_input("Mã nhân viên", placeholder="Nhập ID nhân viên để thao tác...", label_visibility="collapsed").strip().upper()

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
            
            # --- CỘT TRÁI: CẤP PHÁT MỚI ---
            with col_assign:
                st.markdown("#### 📦 Bàn giao thiết bị")
                available = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
                
                if available.data:
                    with st.form("assign_form"):
                        asset_options = {f"{a['asset_tag']} ({a['type'].upper()})": a for a in available.data}
                        target_label = st.selectbox("Chọn thiết bị từ kho", list(asset_options.keys()))
                        date_assign = st.date_input("Ngày bàn giao", value=datetime.now())
                        
                        if st.form_submit_button("Xác nhận bàn giao"):
                            selected_asset = asset_options[target_label]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, 
                                "status": "Đang sử dụng",
                                "purchase_date": str(date_assign)
                            }).eq("id", selected_asset['id']).execute()
                            st.toast(f"Đã bàn giao {selected_asset['asset_tag']}", icon="🚀")
                            st.rerun()
                else:
                    st.info("Hiện không có thiết bị trống trong kho.")

            # --- CỘT PHẢI: THIẾT BỊ ĐANG GIỮ & BẢN QUYỀN ---
            with col_current:
                st.markdown("#### 🖥️ Thiết bị & Phần mềm")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            st.markdown(f"**{a['asset_tag']}** <span class='badge badge-green'>{a['type'].upper()}</span>", unsafe_allow_html=True)
                            
                            # Xử lý software_list an toàn
                            softwares = a.get('software_list')
                            if not isinstance(softwares, list): softwares = []
                            
                            if softwares:
                                st.markdown(f"<small>🛡️ **Bản quyền:** {', '.join(softwares)}</small>", unsafe_allow_html=True)
                            else:
                                st.caption("⚪ Chưa gán bản quyền phần mềm")

                            # Gán License mới
                            with st.expander("Gán License (Trừ kho)"):
                                lic_res = supabase.table("licenses").select("*").execute()
                                if lic_res.data:
                                    # Chỉ hiện license còn số lượng (Remaining > 0)
                                    options = [l for l in lic_res.data if (l.get('total_quantity', 0) - l.get('used_quantity', 0)) > 0]
                                    
                                    if options:
                                        lic_names = [l['name'] for l in options]
                                        selected_lic = st.selectbox("Chọn phần mềm", ["-- Chọn phần mềm --"] + lic_names, key=f"lic_sel_{a['id']}")
                                        
                                        if st.button("Cài đặt & Trừ kho", key=f"btn_lic_{a['id']}") and selected_lic != "-- Chọn phần mềm --":
                                            if selected_lic not in softwares:
                                                # 1. Update máy
                                                softwares.append(selected_lic)
                                                supabase.table("assets").update({"software_list": softwares}).eq("id", a['id']).execute()
                                                
                                                # 2. Update kho License
                                                target_l = next(l for l in options if l['name'] == selected_lic)
                                                supabase.table("licenses").update({
                                                    "used_quantity": (target_l.get('used_quantity', 0) + 1)
                                                }).eq("id", target_l['id']).execute()
                                                
                                                st.success(f"Đã cài {selected_lic}")
                                                st.rerun()
                                            else:
                                                st.warning("Máy này đã cài phần mềm này rồi.")
                                    else:
                                        st.error("Hết bản quyền trong kho!")

                            if st.button("Thu hồi thiết bị", key=f"ret_{a['id']}", use_container_width=True):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("id", a['id']).execute()
                                st.rerun()
                else:
                    st.write("*(Nhân viên này hiện không giữ thiết bị nào)*")

            # --- PHẦN BẢO TRÌ ---
            # --- TRONG PHẦN NHẬT KÝ BẢO TRÌ ---
if my_assets.data:
    st.markdown("### 🛠️ Nhật ký bảo trì")
    
    # TẠO DICTIONARY ĐỂ MAP: "Asset Tag" -> "ID"
    # Ví dụ: {"MN0003": 12, "LT0002": 9}
    asset_map = {a['asset_tag']: a['id'] for a in my_assets.data}
    
    with st.expander("Ghi nhận bảo trì/sửa chữa mới"):
        with st.form("maint_quick_form"):
            # Hiển thị Asset Tag cho người dùng chọn
            selected_tag = st.selectbox("Chọn thiết bị", list(asset_map.keys()))
            
            m_type = st.selectbox("Loại hình", ["Bảo trì định kỳ", "Sửa chữa", "Cài đặt"])
            m_note = st.text_area("Nội dung xử lý")
            
            if st.form_submit_button("Lưu nhật ký"):
                # LẤY ID SỐ NGUYÊN TỪ MAP ĐÃ TẠO
                target_id = asset_map[selected_tag] 
                
                try:
                    # Gửi target_id (số nguyên) thay vì selected_tag (chuỗi)
                    supabase.table("maintenance_log").insert({
                        "asset_id": target_id, 
                        "action_type": m_type,
                        "description": m_note, 
                        "performed_at": str(datetime.now().date())
                    }).execute()
                    
                    st.success(f"Đã lưu bảo trì cho {selected_tag}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi hệ thống: {e}")

# Lưu ý: Đảm bảo bạn gọi render_inventory(supabase) trong file main của bạn.
