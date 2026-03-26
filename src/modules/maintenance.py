import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import plotly.express as px

def render_maintenance(supabase):
    # --- 0. KHỞI TẠO BIẾN THỜI GIAN NGAY ĐẦU HÀM ---
    # Việc đặt ở đây đảm bảo 'today' luôn tồn tại dù có dữ liệu hay không
    today = date.today()

    # --- 1. CSS CUSTOM CHUẨN APPLE ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .stMetric { background: #f5f5f7; padding: 15px; border-radius: 12px; border: 1px solid #d2d2d7; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🛠️ Nhật ký Bảo trì & Vận hành</h1>', unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU (ĐÃ FIX LỖI AMBIGUOUS) ---
    # Sử dụng assets!fk_assets để chỉ định rõ mối quan hệ
    res = supabase.table("maintenance_log").select("*, assets!fk_assets(asset_tag)").order("performed_at", desc=True).execute()
    logs_df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. HỆ THỐNG CẢNH BÁO ---
    if not logs_df.empty:
        logs_df['performed_at'] = pd.to_datetime(logs_df['performed_at']).dt.date
        logs_df['cost'] = pd.to_numeric(logs_df['cost']).fillna(0)
        
        six_months_ago = today - timedelta(days=180)
        latest_maint = logs_df.sort_values('performed_at').groupby('asset_id').last()
        
        # Sửa lỗi truy cập lồng nhau cho join table
        overdue_list = latest_maint[latest_maint['performed_at'] < six_months_ago]

        if not overdue_list.empty:
            st.error(f"🚨 **Cảnh báo:** Có {len(overdue_list)} thiết bị đã quá 6 tháng chưa bảo trì!")
            with st.expander("Xem danh sách chi tiết"):
                for _, row in overdue_list.iterrows():
                    # Lấy asset_tag từ cấu trúc trả về của Supabase
                    tag = row['assets']['asset_tag'] if row.get('assets') else "Unknown"
                    st.write(f"• **{tag}**: Lần cuối là {row['performed_at']}")

    # --- 4. THỐNG KÊ CHI PHÍ ---
    c1, c2, c3 = st.columns(3)
    if not logs_df.empty:
        total_cost = logs_df['cost'].sum()
        this_month_cost = logs_df[pd.to_datetime(logs_df['performed_at']).dt.month == today.month]['cost'].sum()
        c1.metric("Tổng chi phí", f"{total_cost:,.0f} VNĐ")
        c2.metric("Tháng này", f"{this_month_cost:,.0f} VNĐ")
        c3.metric("Số lượt ghi nhận", len(logs_df))
    else:
        c1.metric("Tổng chi phí", "0 VNĐ")
        c2.metric("Tháng này", "0 VNĐ")
        c3.metric("Số lượt ghi nhận", "0")

    st.markdown("---")

    # --- 5. FORM GHI NHẬN (ĐÃ FIX LỖI SUBMIT BUTTON) ---
    with st.expander("➕ Ghi nhận bảo trì/nâng cấp mới", expanded=True):
        # Đảm bảo mọi input đều nằm trong st.form
        with st.form("maintenance_form_v2", clear_on_submit=True):
            assets_res = supabase.table("assets").select("id, asset_tag").execute()
            asset_dict = {a['asset_tag']: a['id'] for a in assets_res.data} if assets_res.data else {}
            
            col_a, col_b, col_c = st.columns(3)
            asset_tag = col_a.selectbox("Chọn thiết bị", options=list(asset_dict.keys()))
            action_type = col_b.selectbox("Loại hình", ["Vệ sinh", "Sửa chữa", "Nâng cấp", "Thay mới"])
            p_date = col_c.date_input("Ngày thực hiện", value=today)
            
            description = st.text_area("Nội dung chi tiết")
            
            c_cost, c_next = st.columns(2)
            cost_val = c_cost.number_input("Chi phí (VNĐ)", min_value=0, step=10000)
            next_date = c_next.date_input("Hẹn bảo trì tiếp theo", value=today + timedelta(days=180))

            # Nút Submit PHẢI nằm trong khối 'with st.form'
            submitted = st.form_submit_button("Lưu thông tin", type="primary")
            
            if submitted:
                if not asset_tag:
                    st.warning("Vui lòng chọn thiết bị!")
                else:
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
                        st.success(f"✅ Đã lưu cho {asset_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    # --- 6. LỊCH SỬ ---
    if not logs_df.empty:
        st.markdown("### 📜 Lịch sử bảo trì")
        # Fix cách hiển thị asset_tag trong dataframe
        display_df = logs_df.copy()
        display_df['Thiết bị'] = display_df['assets'].apply(lambda x: x['asset_tag'] if x else "N/A")
        
        st.dataframe(
            display_df[['performed_at', 'Thiết bị', 'action_type', 'description', 'cost']],
            use_container_width=True,
            hide_index=True
        )
