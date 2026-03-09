import streamlit as st
import pandas as pd

def render_servers(supabase):
    st.markdown('<h2 style="color: #1d1d1f; font-weight: 700;">🖥️ Infrastructure Management</h2>', unsafe_allow_html=True)
    
    try:
        # 1. DATA INGESTION
        res_servers = supabase.table("assets").select("*").eq("type", "server").execute()
        df_servers = pd.DataFrame(res_servers.data) if res_servers.data else pd.DataFrame()
        
        # 2. CHUẨN HÓA DỮ LIỆU (FIX LỖI DATETIME)
        if not df_servers.empty:
            # Chuyển đổi cột expiry sang datetime, lỗi gán NaT (Not a Time)
            df_servers['license_expiry'] = pd.to_datetime(df_servers['license_expiry'], errors='coerce')
            df_servers['last_maintenance'] = df_servers['last_maintenance'].fillna("Chưa có dữ liệu")
            
            # Lấy thời gian hiện tại chuẩn Pandas (loại bỏ giờ/phút/giây để so sánh chính xác)
            now = pd.Timestamp.now().normalize()
            
            # Tính số ngày còn lại (Trả về Series kiểu số nguyên)
            df_servers['days_left'] = (df_servers['license_expiry'] - now).dt.days

        # 3. BỘ LỌC CHI NHÁNH
        branch_options = ["Tất cả", "Miền Bắc (MB)", "TP. Hồ Chí Minh (HCM)", "Long An (LA)", "Đà Nẵng (DN)"]
        selected_branch = st.segmented_control("Chọn khu vực hạ tầng:", branch_options, default="Tất cả")
        
        branch_code = selected_branch.split("(")[-1].replace(")", "") if "(" in selected_branch else ""
        df_display = df_servers[df_servers['asset_tag'].str.contains(branch_code)] if not df_servers.empty and branch_code else df_servers

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
        return

    # --- 4. TỔNG QUAN HẠ TẦNG (METRICS) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tổng số Server", len(df_display))
    with c2:
        online_count = len(df_display[df_display['status'] == 'Đang sử dụng']) if not df_display.empty else 0
        st.metric("Đang vận hành", online_count)
    with c3:
        # Đếm các máy có days_left <= 30 (bỏ qua các giá trị NaN/NaT)
        risk_count = 0
        if not df_display.empty:
            risk_count = df_display['days_left'].le(30).sum()
        st.metric("Rủi ro License", f"{int(risk_count)} máy", delta="Hạn < 30 ngày", delta_color="inverse")

    # --- 5. DANH SÁCH CHI TIẾT ---
    st.markdown("---")
    if not df_display.empty:
        # Sắp xếp để máy sắp hết hạn hiện lên đầu
        df_sorted = df_display.sort_values(by='days_left', ascending=True, na_position='last')
        
        for _, server in df_sorted.iterrows():
            # Xác định trạng thái màu sắc theo chuẩn Apple
            status_color = "#8e8e93" # Xám (Không có hạn)
            expiry_label = "Chưa gán hạn bản quyền"
            
            if pd.notnull(server['days_left']):
                days = int(server['days_left'])
                date_str = server['license_expiry'].strftime('%d/%m/%Y')
                expiry_label = f"Hết hạn: {date_str} ({days} ngày)"
                
                if days <= 15: status_color = "#ff3b30"   # Đỏ
                elif days <= 45: status_color = "#ff9500" # Cam
                else: status_color = "#34c759"           # Xanh

            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"### 🛰️ {server['asset_tag']}")
                    st.markdown(f'<span style="color:{status_color}; font-weight:700;">● {expiry_label}</span>', unsafe_allow_html=True)
                    st.caption(f"Trạng thái: {server['status']} | Bảo trì lần cuối: {server['last_maintenance']}")
                    
                    specs = server.get('specs', {})
                    if isinstance(specs, dict) and specs.get('note'):
                        st.markdown(f"📦 **Cấu hình:** `{specs['note']}`")

                with col_action:
                    st.write("") 
                    with st.popover("➕ Cấp License", use_container_width=True):
                        st.markdown(f"**Gán License cho {server['asset_tag']}**")
                        res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                        
                        if res_lic.data:
                            lic_options = {f"{l['name']} (Còn {l['total_quantity'] - l['used_quantity']})": l for l in res_lic.data}
                            pick_lic = st.selectbox("Chọn phần mềm", list(lic_options.keys()), key=f"lic_{server['id']}")
                            exp_pick = st.date_input("Ngày hết hạn mới", key=f"exp_{server['id']}")
                            
                            if st.button("Xác nhận gán", key=f"btn_{server['id']}", type="primary"):
                                selected_sw = lic_options[pick_lic]
                                current_sw = server.get('software_list') or []
                                
                                if selected_sw['name'] not in current_sw:
                                    current_sw.append(selected_sw['name'])
                                    # Cập nhật DB
                                    supabase.table("assets").update({
                                        "software_list": current_sw,
                                        "license_expiry": exp_pick.isoformat()
                                    }).eq("id", server['id']).execute()
                                    
                                    supabase.table("licenses").update({
                                        "used_quantity": selected_sw['used_quantity'] + 1
                                    }).eq("id", selected_sw['id']).execute()
                                    
                                    st.success("Hệ thống đã cập nhật!")
                                    st.rerun()
                                else:
                                    st.warning("Server này đã được gán bản quyền này.")
                        else:
                            st.info("Kho bản quyền đã hết.")
    else:
        st.info(f"Không có máy chủ nào tại khu vực {selected_branch}.")

    # --- 6. ADMIN: NHẬP KHO (FIXED CONSTRAINT) ---
    with st.expander("📥 Nhập kho Máy chủ mới"):
        with st.form("add_server_v2", clear_on_submit=True):
            c1, c2 = st.columns(2)
            s_id = c1.text_input("Số hiệu Server (VD: 009)")
            s_br = c2.selectbox("Chi nhánh", ["MB", "HCM", "LA", "PP", "DN"])
            s_spec = st.text_area("Cấu hình chi tiết (CPU, RAM, OS...)")
            
            if st.form_submit_button("Xác nhận nhập kho"):
                if s_id:
                    new_tag = f"SV{s_id.strip().upper()}-{s_br}"
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag,
                            "type": "server", # Luôn dùng 'server' cho Database check constraint
                            "status": "Trong kho",
                            "specs": {"note": s_spec},
                            "created_at": pd.Timestamp.now().isoformat()
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag}", icon="🚀")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Lỗi Database: {ex}")
