import streamlit as st
import pandas as pd
from datetime import datetime

def render_servers(supabase):
    st.markdown('<h2 style="color: #1d1d1f; font-weight: 700;">🖥️ Infrastructure Management</h2>', unsafe_allow_html=True)
    
    # --- 1. LẤY DỮ LIỆU & BỘ LỌC CHI NHÁNH ---
    try:
        # Lấy danh sách máy chủ (type='server')
        res_servers = supabase.table("assets").select("*").eq("type", "server").execute()
        df_servers = pd.DataFrame(res_servers.data) if res_servers.data else pd.DataFrame()
        
        # Xử lý giá trị null cho ngày bảo trì để tránh lỗi hiển thị
        if not df_servers.empty:
            df_servers['last_maintenance'] = df_servers['last_maintenance'].fillna("Chưa có dữ liệu")
            # Giả định cột license_expiry tồn tại, nếu không sẽ tạo dữ liệu giả để test
            if 'license_expiry' not in df_servers.columns:
                df_servers['license_expiry'] = None

        branch_options = ["Tất cả", "Miền Bắc (MB)", "TP. Hồ Chí Minh (HCM)", "Long An (LA)", "Đà Nẵng (DN)"]
        selected_branch = st.segmented_control("Chọn khu vực hạ tầng:", branch_options, default="Tất cả")
        
        branch_code = selected_branch.split("(")[-1].replace(")", "") if "(" in selected_branch else ""
        
        if not df_servers.empty and branch_code:
            df_display = df_servers[df_servers['asset_tag'].str.contains(branch_code)]
        else:
            df_display = df_servers

    except Exception as e:
        st.error(f"Lỗi tải hạ tầng: {e}")
        return

    # --- 2. TỔNG QUAN HẠ TẦNG (METRICS) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tổng số Server", len(df_display))
    with c2:
        online_count = len(df_display[df_display['status'] == 'Đang sử dụng']) if not df_display.empty else 0
        st.metric("Đang vận hành", online_count)
    with c3:
        # Check các server sắp hết hạn license (trong vòng 30 ngày)
        expiry_soon = 0
        if not df_display.empty:
            today = datetime.now().date()
            valid_exp = pd.to_datetime(df_display['license_expiry']).dt.date.dropna()
            expiry_soon = sum((valid_exp - today).apply(lambda x: x.days <= 30))
        st.metric("Rủi ro License", expiry_soon, delta="Sắp hết hạn", delta_color="inverse")

    # --- 3. THEO DÕI HẠN & CHI TIẾT ---
    st.markdown("---")
    if not df_display.empty:
        for _, server in df_display.iterrows():
            # Tính toán màu sắc cảnh báo ngày hết hạn
            status_color = "#8e8e93" # Mặc định xám
            expiry_text = "Không có thông tin hạn"
            
            if server['license_expiry']:
                exp_date = pd.to_datetime(server['license_expiry']).date()
                days_left = (exp_date - datetime.now().date()).days
                expiry_text = f"Hết hạn: {exp_date} ({days_left} ngày)"
                if days_left <= 15: status_color = "#ff3b30" # Đỏ
                elif days_left <= 45: status_color = "#ff9500" # Cam
                else: status_color = "#34c759" # Xanh

            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"### 🛰️ {server['asset_tag']}")
                    # Badge trạng thái hết hạn
                    st.markdown(f'<span style="color:{status_color}; font-weight:600;">● {expiry_text}</span>', unsafe_allow_html=True)
                    st.caption(f"Trạng thái: {server['status']} | Bảo trì lần cuối: {server['last_maintenance']}")
                    
                    sw_list = server.get('software_list') or []
                    if sw_list:
                        st.markdown("**Bản quyền hiện có:** " + " ".join([f"`{sw}`" for sw in sw_list]))

                with col_action:
                    st.write("") 
                    with st.popover("➕ Cấp License", use_container_width=True):
                        st.markdown(f"**Gán bản quyền cho {server['asset_tag']}**")
                        # Fix lỗi remaining_qty bằng cách tính trực tiếp
                        res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                        
                        if res_lic.data:
                            # Tính toán số lượng còn lại ngay trong code
                            lic_options = {f"{l['name']} (Còn {l['total_quantity'] - l['used_quantity']})": l for l in res_lic.data}
                            pick_lic = st.selectbox("Chọn phần mềm", list(lic_options.keys()), key=f"lic_{server['id']}")
                            exp_pick = st.date_input("Ngày hết hạn (nếu có)", key=f"exp_{server['id']}")
                            
                            if st.button("Xác nhận gán", key=f"btn_{server['id']}", type="primary"):
                                selected_sw = lic_options[pick_lic]
                                current_sw = server.get('software_list') or []
                                
                                if selected_sw['name'] not in current_sw:
                                    current_sw.append(selected_sw['name'])
                                    # Cập nhật cả software_list và ngày hết hạn
                                    supabase.table("assets").update({
                                        "software_list": current_sw,
                                        "license_expiry": str(exp_pick)
                                    }).eq("id", server['id']).execute()
                                    
                                    supabase.table("licenses").update({
                                        "used_quantity": selected_sw['used_quantity'] + 1
                                    }).eq("id", selected_sw['id']).execute()
                                    
                                    st.success("Đã cập nhật hệ thống!")
                                    st.rerun()
                        else:
                            st.info("Không còn license khả dụng.")
    else:
        st.info(f"Không tìm thấy máy chủ nào thuộc khu vực {selected_branch}.")

    # --- 4. ADMIN: THÊM SERVER MỚI (FIXED CHECK CONSTRAINT) ---
    with st.expander("📥 Nhập kho Máy chủ mới"):
        with st.form("add_server_form_fixed"):
            c1, c2 = st.columns(2)
            s_id = c1.text_input("Mã số máy (VD: 005)")
            s_br = c2.selectbox("Chi nhánh", ["MB", "HCM", "LA", "PP", "DN"])
            s_spec = st.text_area("Cấu hình chi tiết")
            
            if st.form_submit_button("Xác nhận nhập kho"):
                if s_id:
                    # FIX: Luôn sử dụng 'server' để khớp với check constraint của DB
                    new_tag = f"SV{s_id.strip().upper()}-{s_br}"
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag,
                            "type": "server", 
                            "status": "Trong kho",
                            "specs": {"note": s_spec},
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.success(f"Đã thêm {new_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")
