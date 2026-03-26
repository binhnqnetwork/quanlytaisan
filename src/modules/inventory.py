import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH & STYLE ---
    type_mapping = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}

    # --- 2. TRUY XUẤT DỮ LIỆU ---
    # Lấy Assets và Staff để merge thông tin
    res_assets = supabase.table("assets").select("*").order("asset_tag").execute()
    res_staff = supabase.table("staff").select("employee_code, full_name, department, branch").execute()
    
    df_a = pd.DataFrame(res_assets.data) if res_assets.data else pd.DataFrame()
    df_s = pd.DataFrame(res_staff.data) if res_staff.data else pd.DataFrame()

    st.title("📦 Asset Management")
    
    if df_a.empty:
        st.info("Kho đang trống. Vui lòng nhập thiết bị mới.")
    else:
        # --- 3. GIAO DIỆN QUẢN LÝ TÀI SẢN ---
        tab_view, tab_edit = st.tabs(["🔍 Danh mục tổng quát", "⚙️ Chỉnh sửa & Thanh lý"])

        with tab_view:
            # Bộ lọc vùng miền
            vung_filter = st.segmented_control(
                "Lọc theo vùng:", ["Tất cả"] + list(branch_map.keys()), default="Tất cả"
            )
            
            df_display = df_a.copy()
            if vung_filter != "Tất cả":
                suffix = branch_map[vung_filter]
                df_display = df_display[df_display['asset_tag'].str.contains(f"-{suffix}", na=False)]

            # Xử lý hiển thị software_list (list -> string)
            df_display['software_list'] = df_display['software_list'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) and len(x) > 0 else "---"
            )

            # FIX LỖI: Sử dụng TextColumn thay vì BadgeColumn
            st.dataframe(
                df_display[['asset_tag', 'type', 'status', 'assigned_to_code', 'software_list']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "asset_tag": "🔖 Mã máy",
                    "type": "🖥️ Loại",
                    "status": st.column_config.TextColumn("📊 Trạng thái"), # Đã sửa lỗi ở đây
                    "assigned_to_code": "👤 Mã NV",
                    "software_list": "📜 Bản quyền"
                }
            )

        with tab_edit:
            st.markdown("#### 🛠️ Cập nhật hoặc Thu hồi thiết bị")
            
            # Chọn máy cần xử lý
            target_tag = st.selectbox("🎯 Chọn thiết bị mục tiêu", options=df_a['asset_tag'].tolist())
            asset_data = df_a[df_a['asset_tag'] == target_tag].iloc[0]

            col_form, col_danger = st.columns([2, 1])

            with col_form:
                with st.form(f"form_edit_{target_tag}"):
                    st.write(f"Đang chỉnh sửa: **{target_tag}**")
                    
                    # Cho phép sửa trạng thái
                    current_status = asset_data['status']
                    status_options = ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý", "Đã thanh lý"]
                    idx = status_options.index(current_status) if current_status in status_options else 0
                    
                    new_status = st.selectbox("Cập nhật trạng thái", status_options, index=idx)
                    
                    # Sửa ghi chú cấu hình
                    specs = asset_data.get('specs') or {}
                    if isinstance(specs, str): specs = {"note": specs}
                    new_note = st.text_area("Ghi chú cấu hình/Tình trạng", value=specs.get('note', ''))
                    
                    if st.form_submit_button("✅ Cập nhật thay đổi", type="primary"):
                        supabase.table("assets").update({
                            "status": new_status,
                            "specs": {"note": new_note}
                        }).eq("id", asset_data['id']).execute()
                        st.success("Đã cập nhật dữ liệu thành công!")
                        st.rerun()

            with col_danger:
                st.markdown("---")
                st.warning("**Vùng rủi ro cao**")
                st.caption("Chỉ xóa khi nhập sai. Nếu máy hỏng, hãy đổi trạng thái sang 'Đã thanh lý' để giữ lịch sử.")
                
                confirm = st.checkbox(f"Xác nhận xóa {target_tag}")
                if st.button("🗑️ Xóa vĩnh viễn", disabled=not confirm, use_container_width=True):
                    try:
                        # Thực hiện xóa trong database
                        supabase.table("assets").delete().eq("id", asset_data['id']).execute()
                        st.toast(f"Đã xóa vĩnh viễn {target_tag}", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi khi xóa: {e}")

        # --- 4. THỐNG KÊ NHANH ---
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng thiết bị", len(df_a))
        c2.metric("Đang sử dụng", len(df_a[df_a['status'] == 'Đang sử dụng']))
        c3.metric("Sẵn sàng (Kho)", len(df_a[df_a['status'] == 'Trong kho']))
        c4.metric("Bảo trì/Hỏng", len(df_a[df_a['status'].isin(['Bảo trì', 'Hỏng chờ thanh lý'])]))
