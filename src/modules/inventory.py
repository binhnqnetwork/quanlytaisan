import streamlit as st
import pandas as pd

def render_inventory(supabase):
    # --- 1. CONFIG & MAPPING ---
    status_list = ["Trong kho", "Đang sử dụng", "Bảo trì", "Hỏng chờ thanh lý", "Đã thanh lý"]

    st.title("📦 Asset Management Professional")

    # --- 2. LẤY DỮ LIỆU ĐA CHIỀU (JOIN VỚI BẢNG STAFF) ---
    # Sử dụng 'staff!foreign_key(full_name)' để lấy tên thay vì mã
    # Lưu ý: Thay 'assets_assigned_to_code_fkey' bằng tên khóa ngoại thực tế nếu có lỗi
    query = """
        *, 
        staff!assets_assigned_to_code_fkey(full_name)
    """
    res = supabase.table("assets").select(query).order("asset_tag").execute()
    
    # Xử lý dữ liệu sau khi Join
    if res.data:
        raw_data = []
        for item in res.data:
            # Lấy full_name từ object staff lồng bên trong
            staff_info = item.get('staff')
            item['employee_name'] = staff_info.get('full_name') if staff_info else "N/A (Kho)"
            raw_data.append(item)
        df = pd.DataFrame(raw_data)
    else:
        df = pd.DataFrame()

    if df.empty:
        st.info("Chưa có dữ liệu máy móc.")
        return

    # --- 3. GIAO DIỆN CHÍNH ---
    tab_list, tab_action = st.tabs(["📊 Danh mục & Chỉnh sửa nhanh", "🛠️ Thao tác nâng cao"])

    with tab_list:
        st.markdown("💡 *Mẹo: Bạn có thể sửa trực tiếp Trạng thái ngay trên bảng và nhấn Lưu.*")
        
        # Làm sạch list software để hiển thị đẹp
        df['software_display'] = df['software_list'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
        
        # Cấu hình bảng tương tác
        edited_df = st.data_editor(
            df[['id', 'asset_tag', 'type', 'status', 'employee_name', 'software_display']],
            column_config={
                "id": None, 
                "asset_tag": st.column_config.TextColumn("🔖 Mã máy", disabled=True),
                "type": st.column_config.TextColumn("🖥️ Loại", disabled=True),
                "status": st.column_config.SelectboxColumn(
                    "📊 Trạng thái",
                    options=status_list,
                    required=True
                ),
                "employee_name": st.column_config.TextColumn("👤 Nhân viên sử dụng", disabled=True),
                "software_display": st.column_config.TextColumn("📜 License", disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="inventory_editor"
        )

        if st.button("💾 Lưu thay đổi trạng thái", type="primary"):
            # Logic so sánh để chỉ update những dòng thay đổi
            mask = edited_df['status'] != df['status']
            diff = edited_df[mask]
            if not diff.empty:
                for _, row in diff.iterrows():
                    supabase.table("assets").update({"status": row['status']}).eq("id", row['id']).execute()
                st.success(f"✅ Đã cập nhật cho {len(diff)} máy!")
                st.rerun()

    with tab_action:
        col_del, col_info = st.columns([1, 2])
        with col_del:
            st.subheader("🔥 Khu vực xóa")
            target_del = st.selectbox("Chọn máy muốn xóa", options=df['asset_tag'].tolist())
            asset_id = df[df['asset_tag'] == target_del]['id'].values[0]
            confirm = st.text_input(f"Nhập 'DELETE' để xác nhận xóa {target_del}")
            if st.button("Xóa vĩnh viễn", type="secondary", disabled=(confirm != "DELETE")):
                supabase.table("assets").delete().eq("id", asset_id).execute()
                st.rerun()

        with col_info:
            st.subheader("📝 Chi tiết thiết bị")
            selected_row = df[df['asset_tag'] == target_del].iloc[0]
            # Loại bỏ các cột phụ trước khi show JSON cho sạch
            display_json = selected_row.drop(['software_display', 'employee_name']).to_dict()
            st.json(display_json)

    # --- 4. THỐNG KÊ DASHBOARD MINI ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tổng thiết bị", len(df))
    m2.metric("Sẵn sàng", len(df[df['status'] == "Trong kho"]))
    m3.metric("Đang sử dụng", len(df[df['status'] == "Đang sử dụng"]))
    m4.metric("Cần bảo trì", len(df[df['status'] == "Bảo trì"]))
