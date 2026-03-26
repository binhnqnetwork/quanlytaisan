import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

def render_maintenance(supabase):
    today = date.today()
    st.markdown('<h1 style="font-weight: 700;">🛠️ Quản lý Bảo trì Chuyên nghiệp</h1>', unsafe_allow_html=True)

    # --- 1. LẤY DỮ LIỆU GỐC TỪ ASSETS ĐỂ LÀM BỘ LỌC ---
    # Lấy thêm thông tin chi nhánh và phòng ban
    assets_raw = supabase.table("assets").select("id, asset_tag, department, branch").execute()
    df_assets = pd.DataFrame(assets_raw.data) if assets_raw.data else pd.DataFrame()

    # --- 2. FORM NHẬP LIỆU PHÂN CẤP ---
    with st.expander("➕ Ghi nhận bảo trì theo phân cấp", expanded=True):
        with st.form("maintenance_form_pro", clear_on_submit=True):
            
            # Dòng 1: Bộ lọc phân cấp
            col1, col2, col3 = st.columns(3)
            
            with col1:
                branches = sorted(df_assets['branch'].unique().tolist()) if not df_assets.empty else []
                selected_branch = st.selectbox("📍 Chọn Chi nhánh", options=["Tất cả"] + branches)
            
            with col2:
                # Lọc phòng ban dựa trên chi nhánh đã chọn
                if selected_branch != "Tất cả":
                    filtered_deps = df_assets[df_assets['branch'] == selected_branch]['department'].unique()
                else:
                    filtered_deps = df_assets['department'].unique() if not df_assets.empty else []
                selected_dept = st.selectbox("🏢 Chọn Phòng ban", options=["Tất cả"] + sorted(list(filtered_deps)))

            with col3:
                # Lọc mã máy dựa trên chi nhánh VÀ phòng ban
                mask = pd.Series([True] * len(df_assets))
                if selected_branch != "Tất cả":
                    mask &= (df_assets['branch'] == selected_branch)
                if selected_dept != "Tất cả":
                    mask &= (df_assets['department'] == selected_dept)
                
                final_assets = df_assets[mask]
                asset_dict = {row['asset_tag']: row['id'] for _, row in final_assets.iterrows()}
                selected_asset_tag = st.selectbox("💻 Chọn Mã máy", options=list(asset_dict.keys()), 
                                                 help="Chỉ hiển thị các máy thuộc chi nhánh và phòng ban đã chọn")

            # Dòng 2: Thông tin bảo trì
            st.markdown("---")
            c_type, c_date, c_cost = st.columns([1, 1, 1])
            action_type = c_type.selectbox("Loại hình", ["Vệ sinh máy", "Sửa chữa", "Nâng cấp", "Thay mới"])
            p_date = c_date.date_input("Ngày thực hiện", value=today)
            cost_val = c_cost.number_input("Chi phí (VNĐ)", min_value=0, step=10000)

            description = st.text_area("Chi tiết nội dung (Ví dụ: Thay RAM, cài lại Win, vệ sinh quạt...)")
            next_date = today + timedelta(days=180) # Mặc định 6 tháng sau

            submitted = st.form_submit_button("💾 XÁC NHẬN LƯU NHẬT KÝ", type="primary", use_container_width=True)
            
            if submitted:
                if not selected_asset_tag:
                    st.error("Vui lòng chọn mã máy!")
                else:
                    try:
                        submit_data = {
                            "asset_id": asset_dict[selected_asset_tag],
                            "action_type": action_type,
                            "description": description,
                            "performed_at": str(p_date),
                            "cost": cost_val,
                            "next_scheduled_date": str(next_date)
                        }
                        supabase.table("maintenance_log").insert(submit_data).execute()
                        st.success(f"✅ Đã lưu dữ liệu bảo trì cho máy {selected_asset_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi lưu dữ liệu: {e}")

    # --- 3. PHẦN HIỂN THỊ LỊCH SỬ ---
    st.markdown("### 📜 Nhật ký vận hành gần đây")
    res = supabase.table("maintenance_log").select("*, assets!fk_assets(asset_tag, department, branch)").order("performed_at", desc=True).limit(20).execute()
    
    if res.data:
        history_df = pd.DataFrame(res.data)
        # Làm đẹp dữ liệu để hiển thị
        history_df['Mã máy'] = history_df['assets'].apply(lambda x: x['asset_tag'] if x else "")
        history_df['Phòng ban'] = history_df['assets'].apply(lambda x: x['department'] if x else "")
        history_df['Chi nhánh'] = history_df['assets'].apply(lambda x: x['branch'] if x else "")
        
        st.dataframe(
            history_df[['performed_at', 'Chi nhánh', 'Phòng ban', 'Mã máy', 'action_type', 'cost']],
            column_config={
                "performed_at": "Ngày",
                "cost": st.column_config.NumberColumn("Chi phí", format="%d VNĐ")
            },
            hide_index=True,
            use_container_width=True
        )
