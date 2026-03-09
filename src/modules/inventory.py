import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. STYLE CHUẨN APPLE & ĐỊNH DẠNG ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .apple-card {
            background: #ffffff;
            border-radius: 18px;
            padding: 24px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px;
        }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .badge-blue { background: #e8f2ff; color: #0066cc; }
        .badge-green { background: #e2fbe7; color: #1a7f37; }
        .badge-orange { background: #fff4e5; color: #b76e00; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700; color: #1d1d1f; letter-spacing: -0.5px;">📦 Hệ thống Quản trị Tài sản</h1>', unsafe_allow_html=True)

    # --- 2. THỐNG KÊ NHANH (KPIs) ---
    try:
        c1, c2, c3 = st.columns(3)
        with c1:
            in_stock = supabase.table("assets").select("id", count="exact").eq("status", "Trong kho").execute().count
            st.metric("Sẵn có trong kho", f"{in_stock or 0} TB")
        with c2:
            deployed = supabase.table("assets").select("id", count="exact").eq("status", "Đang sử dụng").execute().count
            st.metric("Đang cấp phát", f"{deployed or 0} TB")
        with c3:
            low_lic = supabase.table("licenses").select("id").execute()
            st.metric("Danh mục phần mềm", f"{len(low_lic.data) if low_lic.data else 0} bản")
    except Exception:
        st.warning("Đang kết nối đến cơ sở dữ liệu...")

    # --- 3. NHẬP KHO THIẾT BỊ MỚI ---
    with st.expander("📥 Nhập thiết bị mới vào hệ thống", expanded=False):
        with st.form("apple_add_stock", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 2, 3])
            new_tag = col1.text_input("Asset Tag", placeholder="VD: PC0001")
            
            type_map = {
                "Laptop": "LT", "Desktop PC": "PC",
                "Monitor": "MN", "Server": "Server", "Khác": "Other"
            }
            selected_label = col2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = col3.text_input("Cấu hình tóm tắt", placeholder="M3 Chip, 16GB RAM...")
            
            if st.form_submit_button("Xác nhận Nhập kho"):
                if new_tag:
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": type_map[selected_label],
                            "status": "Trong kho",
                            "specs": {"note": new_specs},
                            "software_list": []
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag}", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi nhập liệu: {e}")

    # --- 4. TRA CỨU & THAO TÁC THEO NHÂN SỰ ---
    st.markdown("### 👤 Quản lý theo Nhân sự")
    e_code = st.text_input("Nhập Mã nhân viên (Employee Code)", placeholder="VD: NV001...").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <span class="badge badge-blue">Mã NV: {staff['employee_code']}</span>
                    <h2 style="margin: 10px 0 5px 0;">{staff['full_name']}</h2>
                    <p style="color: #86868b; margin: 0;">📍 {staff['department']} | {staff['branch']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            col_assign, col_current = st.columns([1, 1], gap="large")
            
            # --- TRÁI: CẤP PHÁT MỚI ---
            with col_assign:
                st.markdown("#### 📤 Bàn giao thiết bị")
                available = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
                
                if available.data:
                    with st.form("assign_form"):
                        asset_options = {f"{a['asset_tag']} ({a['type']})": a for a in available.data}
                        target_label = st.selectbox("Chọn thiết bị đang trống", list(asset_options.keys()))
                        date_assign = st.date_input("Ngày bàn giao", value=datetime.now())
                        
                        if st.form_submit_button("Xác nhận Bàn giao"):
                            selected_asset = asset_options[target_label]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, 
                                "status": "Đang sử dụng",
                                "purchase_date": str(date_assign)
                            }).eq("id", selected_asset['id']).execute()
                            st.success(f"Đã bàn giao {selected_asset['asset_tag']} cho {staff['full_name']}")
                            st.rerun()
                else:
                    st.info("Không còn thiết bị trống trong kho.")

            # --- PHẢI: THIẾT BỊ ĐANG GIỮ & PHẦN MỀM ---
            with col_current:
                st.markdown("#### 🖥️ Thiết bị & Phần mềm")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            st.markdown(f"**{a['asset_tag']}** <span class='badge badge-green'>{a['type']}</span>", unsafe_allow_html=True)
                            
                            # Xử lý software_list
                            softwares = a.get('software_list') or []
                            if softwares:
                                st.markdown(f"<small>🛡️ **Bản quyền:** {', '.join(softwares)}</small>", unsafe_allow_html=True)
                            
                            # Gán License mới
                            with st.expander("Gán License (Trừ kho)"):
                                lic_res = supabase.table("licenses").select("*").execute()
                                if lic_res.data:
                                    # Fix: Đảm bảo tính toán Remaining chuẩn xác
                                    options = [l for l in lic_res.data if (l.get('total_quantity', 0) - l.get('used_quantity', 0)) > 0]
                                    
                                    if options:
                                        lic_names = [l['name'] for l in options]
                                        selected_lic = st.selectbox("Chọn phần mềm", ["-- Chọn --"] + lic_names, key=f"lic_sel_{a['id']}")
                                        
                                        if st.button("Cài đặt & Trừ kho", key=f"btn_lic_{a['id']}") and selected_lic != "-- Chọn --":
                                            if selected_lic not in softwares:
                                                softwares.append(selected_lic)
                                                # 1. Cập nhật máy
                                                supabase.table("assets").update({"software_list": softwares}).eq("id", a['id']).execute()
                                                # 2. Cập nhật số lượng kho bản quyền
                                                target_l = next(l for l in options if l['name'] == selected_lic)
                                                supabase.table("licenses").update({
                                                    "used_quantity": (target_l.get('used_quantity', 0) + 1)
                                                }).eq("id", target_l['id']).execute()
                                                st.rerun()
                                            else:
                                                st.warning("Đã cài phần mềm này.")
                                    else:
                                        st.error("Hết bản quyền khả dụng!")

                            if st.button("Thu hồi thiết bị", key=f"ret_{a['id']}", use_container_width=True):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("id", a['id']).execute()
                                st.rerun()
                else:
                    st.write("*(Chưa có thiết bị cấp phát)*")

            # --- 5. NHẬT KÝ BẢO TRÌ (FIXED ID ERROR) ---
            if my_assets.data:
                st.markdown("---")
                st.markdown("### 🛠️ Nhật ký bảo trì & Sửa chữa")
                
                # Ánh xạ từ Tag sang ID để tránh lỗi 22P02
                asset_map = {a['asset_tag']: a['id'] for a in my_assets.data}
                
                with st.expander("Ghi nhận bảo trì mới"):
                    with st.form("maint_form"):
                        target_tag = st.selectbox("Thiết bị", list(asset_map.keys()))
                        m_type = st.selectbox("Loại hình", ["Bảo trì định kỳ", "Sửa chữa", "Thay thế linh kiện"])
                        m_note = st.text_area("Chi tiết xử lý")
                        
                        if st.form_submit_button("Lưu lịch sử"):
                            try:
                                supabase.table("maintenance_log").insert({
                                    "asset_id": asset_map[target_tag], # Gửi ID số nguyên
                                    "action_type": m_type,
                                    "description": m_note,
                                    "performed_at": str(datetime.now().date())
                                }).execute()
                                st.success(f"Đã lưu lịch sử bảo trì cho {target_tag}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi RLS hoặc Dữ liệu: {e}")
        else:
            st.error("Không tìm thấy nhân viên này trong hệ thống. Vui lòng kiểm tra lại mã.")
