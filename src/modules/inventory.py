import streamlit as st
import pandas as pd

def render_inventory(supabase):
    # --- 1. CONFIG & MAPPING ---
    type_map = {"Desktop PC": "pc", "Laptop": "laptop", "Server": "server", "Monitor": "monitor"}
    branch_map = {"Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"}
    status_list = ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý", "Đã thanh lý"]

    st.title("📦 Asset Management Professional")

    # --- 2. LẤY DỮ LIỆU ---
    res = supabase.table("assets").select("*").order("asset_tag").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    if df.empty:
        st.info("Chưa có dữ liệu máy móc.")
        return

    # --- 3. GIAO DIỆN CHÍNH ---
    tab_list, tab_action = st.tabs(["📊 Danh mục & Chỉnh sửa nhanh", "🛠️ Thao tác nâng cao"])

    with tab_list:
        st.markdown("💡 *Mẹo: Bạn có thể sửa trực tiếp Trạng thái hoặc Ghi chú ngay trên bảng dưới đây.*")
        
        # Làm sạch dữ liệu hiển thị
        df['software_list'] = df['software_list'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
        
        # Cấu hình bảng tương tác (Data Editor)
        # Thay vì chỉ xem, ta dùng data_editor để Pro hơn
        edited_df = st.data_editor(
            df[['id', 'asset_tag', 'type', 'status', 'assigned_to_code', 'software_list']],
            column_config={
                "id": None, # Ẩn cột ID
                "asset_tag": st.column_config.TextColumn("🔖 Mã máy", disabled=True),
                "type": st.column_config.TextColumn("🖥️ Loại", disabled=True),
                "status": st.column_config.SelectboxColumn(
                    "📊 Trạng thái",
                    options=status_list,
                    required=True,
                    help="Thay đổi trạng thái máy tại đây"
                ),
                "assigned_to_code": st.column_config.TextColumn("👤 Nhân viên", disabled=True),
                "software_list": st.column_config.TextColumn("📜 License", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="inventory_editor"
        )

        # Nút lưu thay đổi nhanh từ bảng
        if st.button("💾 Lưu thay đổi trên bảng"):
            # Tìm các dòng có sự thay đổi (so sánh df gốc và edited_df)
            diff = edited_df[edited_df['status'] != df['status']]
            if not diff.empty:
                for _, row in diff.iterrows():
                    supabase.table("assets").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success(f"✅ Đã cập nhật trạng thái cho {len(diff)} máy!")
                st.rerun()

    with tab_action:
        col_del, col_info = st.columns([1, 2])
        
        with col_del:
            st.subheader("🔥 Khu vực xóa")
            target_del = st.selectbox("Chọn máy muốn xóa", options=df['asset_tag'].tolist())
            asset_id = df[df['asset_tag'] == target_del]['id'].values[0]
            
            confirm = st.text_input(f"Nhập 'DELETE' để xác nhận xóa {target_del}")
            if st.button("Xóa vĩnh viễn", type="primary", disabled=(confirm != "DELETE")):
                supabase.table("assets").delete().eq("id", asset_id).execute()
                st.toast(f"Đã xóa {target_del}")
                st.rerun()

        with col_info:
            st.subheader("📝 Chi tiết thiết bị")
            # Hiển thị thông tin chi tiết dưới dạng JSON hoặc Table cho máy đang chọn ở trên
            selected_row = df[df['asset_tag'] == target_del].iloc[0]
            st.json(selected_row.to_dict())

    # --- 4. THỐNG KÊ DASHBOARD ---
    st.markdown("---")
    cols = st.columns(4)
    cols[0].metric("Tổng máy", len(df))
    cols[1].metric("Sẵn sàng", len(df[df['status'] == "Trong kho"]))
    cols[2].metric("Đang dùng", len(df[df['status'] == "Đang sử dụng"]))
    cols[3].metric("Cần xử lý", len(df[df['status'].isin(["Bảo trì", "Hỏng chờ thanh lý"])]))
