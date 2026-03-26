import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. CẤU HÌNH HỆ THỐNG & STYLE (Giữ nguyên từ code của bạn) ---
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
        .stButton>button { border-radius: 12px; transition: 0.3s; }
        </style>
    """, unsafe_allow_html=True)

    st.title("📦 Asset Management")
    st.markdown("### Quản trị Tài sản & Cấp phát")

    # --- 2. TÌM KIẾM NHÂN VIÊN & CẤP PHÁT (Phần code cũ của bạn - Giữ nguyên logic) ---
    # [Giữ nguyên đoạn code xử lý e_code, tab_hw, tab_sw...]
    # (Để tiết kiệm không gian, tôi tập trung vào phần tính năng mới bạn yêu cầu bên dưới)

    # --- 3. QUẢN TRỊ NHẬP KHO ---
    # [Giữ nguyên đoạn code Nhập thiết bị mới...]

    # --- 4. HỆ THỐNG QUẢN LÝ & ĐIỀU CHỈNH TÀI SẢN ---
    st.markdown("---")
    st.markdown("### 📋 Hệ thống Quản lý & Điều chỉnh")
    
    # Truy vấn dữ liệu mới nhất
    res_assets = supabase.table("assets").select("*").order("asset_tag").execute()
    res_staff = supabase.table("staff").select("employee_code, full_name").execute()
    
    if res_assets.data:
        df_a = pd.DataFrame(res_assets.data)
        
        # Tabs phân tách giữa Xem danh sách và Chỉnh sửa
        tab_view, tab_edit = st.tabs(["🔍 Xem danh mục", "⚙️ Chỉnh sửa & Thanh lý"])

        with tab_view:
            # Bộ lọc vùng miền (Segmented Control)
            vung_filter = st.segmented_control(
                "Lọc nhanh:", ["Tất cả"] + list(branch_map.keys()), default="Tất cả"
            )
            
            df_display = df_a.copy()
            if vung_filter != "Tất cả":
                suffix = branch_map[vung_filter]
                df_display = df_display[df_display['asset_tag'].str.contains(f"-{suffix}", na=False)]

            st.dataframe(
                df_display[['asset_tag', 'type', 'status', 'assigned_to_code', 'software_list']],
                use_container_width=True, hide_index=True,
                column_config={"status": st.column_config.BadgeColumn("Trạng thái")}
            )

        with tab_edit:
            st.info("Chọn một thiết bị để cập nhật thông tin hoặc xóa khỏi hệ thống.")
            
            # Chọn máy cần tác động
            target_tag = st.selectbox("🎯 Chọn Mã máy cần xử lý", options=df_a['asset_tag'].tolist())
            asset_data = df_a[df_a['asset_tag'] == target_tag].iloc[0]

            col_edit, col_del = st.columns([2, 1])

            with col_edit:
                st.markdown("**📝 Cập nhật thông tin**")
                with st.form(f"edit_form_{target_tag}"):
                    new_status = st.selectbox("Trạng thái mới", 
                                            ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý"],
                                            index=["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý"].index(asset_data['status']) if asset_data['status'] in ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý"] else 0)
                    
                    # Cho phép sửa Specs (Cấu hình)
                    current_specs = asset_data.get('specs', {})
                    if isinstance(current_specs, str): current_specs = {"note": current_specs}
                    new_note = st.text_area("Cấu hình/Ghi chú", value=current_specs.get('note', ''))
                    
                    if st.form_submit_button("Lưu thay đổi", type="primary"):
                        supabase.table("assets").update({
                            "status": new_status,
                            "specs": {"note": new_note}
                        }).eq("id", asset_data['id']).execute()
                        st.success(f"Đã cập nhật {target_tag}!")
                        st.rerun()

            with col_del:
                st.markdown("**⚠️ Vùng nguy hiểm**")
                st.write("Xóa máy khi đã thanh lý hoặc nhập sai thông tin.")
                
                # Nút xóa với xác nhận kép
                confirm_del = st.checkbox(f"Xác nhận xóa {target_tag}")
                if st.button("🔥 Xóa vĩnh viễn", disabled=not confirm_del, use_container_width=True):
                    # Trước khi xóa, kiểm tra nếu máy đang gán License thì nên cảnh báo (tùy chọn)
                    try:
                        supabase.table("assets").delete().eq("id", asset_data['id']).execute()
                        st.toast(f"Đã xóa {target_tag} khỏi hệ thống", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Không thể xóa: {e}")

        # Thống kê nhanh cuối trang
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng thiết bị", len(df_a))
        c2.metric("Đang sử dụng", len(df_a[df_a['status'] == 'Đang sử dụng']))
        c3.metric("Trong kho", len(df_a[df_a['status'] == 'Trong kho']))
        c4.metric("Cần xử lý", len(df_a[df_a['status'].isin(['Bảo trì', 'Hỏng chờ thanh lý'])]))
