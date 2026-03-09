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
        
        # Lấy danh sách chi nhánh để lọc (Dựa trên asset_tag: SV...-HCM, SV...-MB)
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
        # Giả định server cần bảo trì nếu chưa bảo trì > 180 ngày
        st.metric("Cần kiểm tra", len(df_display[df_display['last_maintenance'].isna()]))

    # --- 3. DANH SÁCH CHI TIẾT & CẤP BẢN QUYỀN ---
    st.markdown("---")
    if not df_display.empty:
        for _, server in df_display.iterrows():
            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"### 🛰️ {server['asset_tag']}")
                    st.caption(f"Trạng thái: {server['status']} | Ngày nhập: {server['created_at'][:10]}")
                    st.markdown(f"**Cấu hình:** `{server['specs'].get('note', 'N/A')}`")
                    
                    # Hiển thị các License hiện có trên Server
                    sw_list = server.get('software_list') or []
                    if sw_list:
                        st.markdown("**Phần mềm đã cài:** " + " ".join([f"`{sw}`" for sw in sw_list]))
                    else:
                        st.markdown("*Chưa có bản quyền phần mềm nào được gán.*")

                with col_action:
                    st.write("") # Spacer
                    # Nút mở rộng để cấp bản quyền ngay tại chỗ
                    with st.popover("➕ Cấp bản quyền", use_container_width=True):
                        st.markdown(f"**Gán License cho {server['asset_tag']}**")
                        # Lấy danh sách license còn trống
                        res_lic = supabase.table("licenses").select("id, name, total_quantity, used_quantity").execute()
                        
                        if res_lic.data:
                            lic_options = {f"{l['name']} (Còn {l['total_quantity']-l['used_quantity']})": l for l in res_lic.data}
                            pick_lic = st.selectbox("Chọn phần mềm", list(lic_options.keys()), key=f"lic_{server['id']}")
                            
                            if st.button("Xác nhận cấp", key=f"btn_{server['id']}", type="primary"):
                                selected_sw = lic_options[pick_lic]
                                
                                # 1. Cập nhật software_list của server
                                current_sw = server.get('software_list') or []
                                if selected_sw['name'] not in current_sw:
                                    current_sw.append(selected_sw['name'])
                                    supabase.table("assets").update({"software_list": current_sw}).eq("id", server['id']).execute()
                                    
                                    # 2. Trừ số lượng trong bảng licenses
                                    supabase.table("licenses").update({
                                        "used_quantity": selected_sw['used_quantity'] + 1
                                    }).eq("id", selected_sw['id']).execute()
                                    
                                    st.success(f"Đã gán {selected_sw['name']}!")
                                    st.rerun()
                                else:
                                    st.warning("Server này đã có bản quyền này.")
                        else:
                            st.info("Không còn license trống.")
    else:
        st.info(f"Không tìm thấy máy chủ nào thuộc khu vực {selected_branch}.")

    # --- 4. ADMIN: THÊM SERVER MỚI ---
    with st.expander("📥 Thêm Máy chủ mới vào hệ thống"):
        with st.form("add_server_form"):
            c_id, c_br = st.columns(2)
            s_id = c_id.text_input("Mã số Server (VD: 001)")
            s_br = c_br.selectbox("Chi nhánh", ["MB", "HCM", "LA", "PP", "DN"])
            s_spec = st.text_area("Thông số kỹ thuật (CPU, RAM, Storage, OS...)")
            
            if st.form_submit_button("Xác nhận nhập kho Server"):
                if s_id:
                    new_tag = f"SV{s_id.strip().upper()}-{s_br}"
                    supabase.table("assets").insert({
                        "asset_tag": new_tag,
                        "type": "server",
                        "status": "Trong kho",
                        "specs": {"note": s_spec}
                    }).execute()
                    st.toast(f"Đã thêm Server {new_tag}", icon="🚀")
                    st.rerun()
