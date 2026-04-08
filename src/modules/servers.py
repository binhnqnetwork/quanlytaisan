import streamlit as st
import pandas as pd

def render_servers(supabase):
    st.markdown('<h2 style="color: #1d1d1f; font-weight: 700;">🖥️ Infrastructure Management</h2>', unsafe_allow_html=True)
    
    try:
        # 1. DATA INGESTION
        res_servers = supabase.table("assets").select("*").eq("type", "server").execute()
        df_servers = pd.DataFrame(res_servers.data) if res_servers.data else pd.DataFrame()
        
        # 2. CHUẨN HÓA DỮ LIỆU
        if not df_servers.empty:
            # FIX LỖI: Đảm bảo asset_tag luôn là chuỗi, thay thế None bằng chuỗi rỗng
            df_servers['asset_tag'] = df_servers['asset_tag'].fillna('').astype(str)
            
            # Chuyển đổi cột expiry sang datetime
            df_servers['license_expiry'] = pd.to_datetime(df_servers['license_expiry'], errors='coerce')
            df_servers['last_maintenance'] = df_servers['last_maintenance'].fillna("Chưa có dữ liệu")
            
            # Lấy thời gian hiện tại chuẩn Pandas
            now = pd.Timestamp.now().normalize()
            
            # Tính số ngày còn lại (An toàn với giá trị NaT)
            df_servers['days_left'] = (df_servers['license_expiry'] - now).dt.days

        # 3. BỘ LỌC CHI NHÁNH
        branch_options = ["Tất cả", "Miền Bắc (MB)", "TP. Hồ Chí Minh (HCM)", "Long An (LA)", "Đà Nẵng (DN)"]
        # Sử dụng segmented_control (Yêu cầu Streamlit 1.35+)
        selected_branch = st.segmented_control("Chọn khu vực hạ tầng:", branch_options, default="Tất cả")
        
        branch_code = selected_branch.split("(")[-1].replace(")", "") if "(" in selected_branch else ""
        
        # FIX LỖI TRIỆT ĐỂ: Kiểm tra DataFrame rỗng trước khi lọc
        if df_servers.empty:
            df_display = df_servers
        elif not branch_code or selected_branch == "Tất cả":
            df_display = df_servers
        else:
            # Lọc an toàn sau khi đã fillna('')
            df_display = df_servers[df_servers['asset_tag'].str.contains(branch_code, case=False, na=False)]

    except Exception as e:
        st.error(f"Lỗi hệ thống: {e}")
        return

    # --- 4. TỔNG QUAN HẠ TẦNG (METRICS) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Tổng số Server", len(df_display))
    with c2:
        # Kiểm tra cột 'status' tồn tại
        status_col = 'status' if 'status' in df_display.columns else None
        online_count = len(df_display[df_display[status_col] == 'Đang sử dụng']) if status_col and not df_display.empty else 0
        st.metric("Đang vận hành", online_count)
    with c3:
        risk_count = 0
        if not df_display.empty and 'days_left' in df_display.columns:
            # Chỉ đếm những máy có hạn dùng cụ thể và <= 30 ngày
            risk_count = df_display['days_left'].dropna().le(30).sum()
        st.metric("Rủi ro License", f"{int(risk_count)} máy", delta="Hạn < 30 ngày", delta_color="inverse")

    # --- 5. DANH SÁCH CHI TIẾT ---
    st.markdown("---")
    if not df_display.empty:
        # Sắp xếp
        df_sorted = df_display.sort_values(by='days_left', ascending=True, na_position='last')
        
        for _, server in df_sorted.iterrows():
            status_color = "#8e8e93" 
            expiry_label = "Chưa gán hạn bản quyền"
            
            # Kiểm tra an toàn trước khi truy cập days_left
            days = server.get('days_left')
            if pd.notnull(days):
                days = int(days)
                date_str = server['license_expiry'].strftime('%d/%m/%Y')
                expiry_label = f"Hết hạn: {date_str} ({days} ngày)"
                
                if days <= 15: status_color = "#ff3b30"
                elif days <= 45: status_color = "#ff9500"
                else: status_color = "#34c759"

            with st.container(border=True):
                col_info, col_action = st.columns([3, 1])
                
                with col_info:
                    st.markdown(f"### 🛰️ {server['asset_tag']}")
                    st.markdown(f'<span style="color:{status_color}; font-weight:700;">● {expiry_label}</span>', unsafe_allow_html=True)
                    st.caption(f"Trạng thái: {server.get('status', 'N/A')} | Bảo trì: {server.get('last_maintenance', 'N/A')}")
                    
                    specs = server.get('specs', {})
                    if isinstance(specs, dict) and specs.get('note'):
                        st.markdown(f"📦 **Cấu hình:** `{specs['note']}`")

                with col_action:
                    st.write("") 
                    with st.popover("➕ Cấp License", use_container_width=True):
                        st.markdown(f"**Gán License cho {server['asset_tag']}**")
                        # (Giữ nguyên logic gán license của bạn...)
                        # Lưu ý: Thêm st.rerun() sau khi cập nhật thành công
    else:
        st.info(f"Không có máy chủ nào tại khu vực {selected_branch}.")

    # --- 6. ADMIN: NHẬP KHO ---
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
                            "type": "server",
                            "status": "Trong kho",
                            "specs": {"note": s_spec},
                            "created_at": pd.Timestamp.now().isoformat()
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag}", icon="🚀")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Lỗi Database: {ex}")
