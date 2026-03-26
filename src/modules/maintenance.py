import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px

def render_maintenance(supabase):
    # --- 1. CSS CUSTOM CHUẨN APPLE ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .stMetric { background: #f5f5f7; padding: 15px; border-radius: 12px; border: 1px solid #d2d2d7; }
        .status-overdue { color: #ff3b30; font-weight: 700; }
        .status-good { color: #34c759; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🛠️ Nhật ký Bảo trì & Vận hành</h1>', unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU ---
    # Lấy dữ liệu log và join với bảng assets để lấy Asset Tag
    res = supabase.table("maintenance_log").select("*, assets(asset_tag)").order("performed_at", desc=True).execute()
    logs_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. HỆ THỐNG CẢNH BÁO CHUYÊN SÂU (PROACTIVE) ---
    if not logs_df.empty:
        # Ép kiểu dữ liệu
        logs_df['performed_at'] = pd.to_datetime(logs_df['performed_at']).dt.date
        logs_df['cost'] = pd.to_numeric(logs_df['cost']).fillna(0)
        
        # Logic cảnh báo: Tìm các thiết bị có lần bảo trì cuối cùng cách đây > 180 ngày (6 tháng)
        today = date.today()
        six_months_ago = today - timedelta(days=180)
        
        # Lấy bản ghi mới nhất của mỗi Asset
        latest_maint = logs_df.sort_values('performed_at').groupby('asset_id').last()
        overdue_list = latest_maint[latest_maint['performed_at'] < six_months_ago]

        if not overdue_list.empty:
            st.error(f"🚨 **Cảnh báo hệ thống:** Có {len(overdue_list)} thiết bị đã quá 6 tháng chưa được bảo trì/vệ sinh định kỳ!")
            with st.expander("Xem danh sách máy cần bảo trì ngay"):
                for idx, row in overdue_list.iterrows():
                    asset_tag = row['assets']['asset_tag'] if row['assets'] else "N/A"
                    st.write(f"• **{asset_tag}**: Lần cuối bảo trì là ngày {row['performed_at']}")

    # --- 4. THỐNG KÊ CHI PHÍ (KPIs) ---
    c1, c2, c3 = st.columns(3)
    if not logs_df.empty:
        total_cost = logs_df['cost'].sum()
        this_month_cost = logs_df[pd.to_datetime(logs_df['performed_at']).dt.month == today.month]['cost'].sum()
        
        c1.metric("Tổng chi phí bảo trì", f"{total_cost:,.0f} VNĐ")
        c2.metric("Chi phí tháng này", f"{this_month_cost:,.0f} VNĐ")
        c3.metric("Số lượt ghi nhận", len(logs_df))
    else:
        c1.metric("Tổng chi phí", "0 VNĐ")
        c2.metric("Chi phí tháng này", "0 VNĐ")

    st.markdown("---")

    # --- 5. FORM GHI NHẬN MỚI (INPUT) ---
    with st.expander("➕ Ghi nhận bảo trì/nâng cấp mới", expanded=False):
        with st.form("add_maintenance_form", clear_on_submit=True):
            # Lấy danh sách máy từ bảng assets
            assets_res = supabase.table("assets").select("id, asset_tag").execute()
            asset_dict = {a['asset_tag']: a['id'] for a in assets_res.data}
            
            col_a, col_b, col_c = st.columns(3)
            asset_tag = col_a.selectbox("Chọn thiết bị", options=list(asset_dict.keys()))
            action_type = col_b.selectbox("Loại hình", ["Vệ sinh định kỳ", "Sửa chữa hỏng hóc", "Nâng cấp linh kiện", "Thay thế mới"])
            p_date = col_c.date_input("Ngày thực hiện", value=today)
            
            description = st.text_area("Nội dung chi tiết (VD: Thay SSD Samsung 500GB, tra keo tản nhiệt)")
            
            c_cost, c_next = st.columns(2)
            cost_val = c_cost.number_input("Chi phí thực hiện (VNĐ)", min_value=0, step=50000)
            next_date = c_next.date_input("Ngày bảo trì dự kiến tiếp theo", value=today + timedelta(days=180))

            if st.form_submit_button("Lưu nhật ký bảo trì", type="primary"):
                try:
                    data = {
                        "asset_id": asset_dict[asset_tag],
                        "action_type": action_type,
                        "description": description,
                        "performed_at": str(p_date),
                        "cost": cost_val,
                        "next_scheduled_date": str(next_date)
                    }
                    supabase.table("maintenance_log").insert(data).execute()
                    st.success(f"✅ Đã lưu lịch sử bảo trì cho {asset_tag}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi khi lưu: {e}")

    # --- 6. LỊCH SỬ CHI TIẾT (TIMELINE) ---
    st.markdown("### 📜 Lịch sử hoạt động toàn hệ thống")
    if not logs_df.empty:
        # Chuẩn bị dữ liệu hiển thị
        display_df = logs_df.copy()
        display_df['Thiết bị'] = display_df['assets'].apply(lambda x: x['asset_tag'] if x else "N/A")
        
        st.dataframe(
            display_df[['performed_at', 'Thiết bị', 'action_type', 'description', 'cost']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "performed_at": st.column_config.DateColumn("Ngày thực hiện"),
                "Thiết bị": st.column_config.TextColumn("Mã máy", width="small"),
                "action_type": st.column_config.TextColumn("Loại hình", width="medium"),
                "description": st.column_config.TextColumn("Nội dung chi tiết", width="large"),
                "cost": st.column_config.NumberColumn("Chi phí (VNĐ)", format="%d")
            }
        )
        
        # Thêm biểu đồ chi phí theo tháng (Analytics)
        st.markdown("### 📊 Phân tích chi phí theo thời gian")
        logs_df['Month-Year'] = pd.to_datetime(logs_df['performed_at']).dt.strftime('%m-%Y')
        cost_chart = logs_df.groupby('Month-Year')['cost'].sum().reset_index()
        fig = px.line(cost_chart, x='Month-Year', y='cost', title='Biểu đồ chi phí IT theo tháng',
                      labels={'cost': 'Chi phí (VNĐ)', 'Month-Year': 'Tháng'},
                      line_shape='spline', markers=True)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Chưa có dữ liệu bảo trì nào. Hãy bắt đầu ghi nhận từ Form phía trên.")
