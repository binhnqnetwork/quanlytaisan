import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

def render_maintenance(supabase):
    st.markdown("## 🛠️ Nhật ký Bảo trì & Nâng cấp")

    # --- 1. TRUY VẤN DỮ LIỆU ---
    # Lấy lịch sử và join với bảng assets để có Asset Tag
    res = supabase.table("maintenance_log").select("*, assets(asset_tag)").execute()
    logs_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 2. CẢNH BÁO THÔNG MINH (PROACTIVE) ---
    if not logs_df.empty:
        # Chuyển đổi ngày tháng an toàn
        logs_df['performed_at'] = pd.to_datetime(logs_df['performed_at'])
        
        # Logic: Tìm các máy đã quá 6 tháng chưa bảo trì (vệ sinh/kiểm tra)
        six_months_ago = datetime.now() - timedelta(days=180)
        # Lấy bản ghi mới nhất của từng asset
        latest_logs = logs_df.sort_values('performed_at').groupby('asset_id').last()
        overdue_assets = latest_logs[latest_logs['performed_at'] < six_months_ago]
        
        if not overdue_assets.empty:
            st.error(f"🚨 **Cảnh báo:** Có {len(overdue_assets)} thiết bị đã quá 6 tháng chưa được bảo trì định kỳ!")

    # --- 3. FORM GHI NHẬN NHANH (MỚI) ---
    with st.expander("➕ Ghi nhận bảo trì/nâng cấp mới", expanded=False):
        with st.form("add_log_form", clear_on_submit=True):
            # Lấy danh sách máy để chọn
            assets_res = supabase.table("assets").select("id, asset_tag").execute()
            asset_list = {a['asset_tag']: a['id'] for a in assets_res.data}
            
            c1, c2, c3 = st.columns([2, 2, 2])
            selected_asset_tag = c1.selectbox("Thiết bị", options=list(asset_list.keys()))
            action_type = c2.selectbox("Loại hình", ["Vệ sinh định kỳ", "Sửa chữa hỏng hóc", "Nâng cấp linh kiện", "Thay thế mới"])
            log_date = c3.date_input("Ngày thực hiện", value=date.today())
            
            description = st.text_area("Chi tiết nội dung (ví dụ: Thay SSD Samsung 500GB, nâng RAM lên 16GB)")
            
            # Cột chi phí (nếu bạn đã thêm cột cost vào DB)
            cost = st.number_input("Chi phí thực hiện (VNĐ)", min_value=0, step=100000)

            if st.form_submit_button("Lưu nhật ký"):
                new_log = {
                    "asset_id": asset_list[selected_asset_tag],
                    "action_type": action_type,
                    "description": description,
                    "performed_at": str(log_date),
                    "cost": cost # Chỉ dùng nếu bạn đã thêm cột cost
                }
                supabase.table("maintenance_log").insert(new_log).execute()
                st.success(f"✅ Đã lưu lịch sử cho máy {selected_asset_tag}")
                st.rerun()

    # --- 4. HIỂN THỊ DÒNG THỜI GIAN (TIMELINE) ---
    st.markdown("### 📜 Lịch sử hoạt động")
    if not logs_df.empty:
        # Làm sạch dữ liệu hiển thị
        display_df = logs_df.copy()
        display_df['Thiết bị'] = display_df['assets'].apply(lambda x: x['asset_tag'] if x else "N/A")
        
        st.dataframe(
            display_df[['performed_at', 'Thiết bị', 'action_type', 'description', 'cost']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "performed_at": st.column_config.DateColumn("📅 Ngày"),
                "action_type": "🔧 Phân loại",
                "description": "📝 Nội dung chi tiết",
                "cost": st.column_config.NumberColumn("💰 Chi phí", format="%d VNĐ")
            }
        )
    else:
        st.info("Chưa có lịch sử bảo trì nào được ghi nhận.")
