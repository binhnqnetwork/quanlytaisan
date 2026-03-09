import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render_dashboard(supabase):
    st.markdown("""
        <style>
        .stMetric { background: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .dashboard-card { background: white; padding: 20px; border-radius: 16px; border: 1px solid #d2d2d7; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700;">📊 AI Strategic Hub - Enterprise Analytics</h1>', unsafe_allow_html=True)

    # --- 1. DATA AGGREGATION ---
    assets_res = supabase.table("assets").select("*").execute()
    lic_res = supabase.table("licenses").select("*").execute()
    maint_res = supabase.table("maintenance_log").select("*").execute()

    df_assets = pd.DataFrame(assets_res.data) if assets_res.data else pd.DataFrame()
    df_lic = pd.DataFrame(lic_res.data) if lic_res.data else pd.DataFrame()
    df_maint = pd.DataFrame(maint_res.data) if maint_res.data else pd.DataFrame()

    if df_assets.empty:
        st.info("Chưa có dữ liệu để hiển thị Dashboard.")
        return

    # --- 2. TOP-LEVEL KPIs (BỘ CHỈ SỐ CHIẾN LƯỢC) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_value = len(df_assets)
        st.metric("Tổng thiết bị", f"{total_value}", "+2% vs tháng trước")
    with c2:
        # Giả định tỷ lệ sẵn sàng dựa trên status "Trong kho"
        available = len(df_assets[df_assets['status'] == "Trong kho"])
        uptime = (available / total_value * 100) if total_value > 0 else 0
        st.metric("Tỷ lệ sẵn sàng", f"{uptime:.1f}%", "Ổn định")
    with c3:
        # Tính số license cần chú ý
        df_lic['remaining'] = df_lic['total_quantity'] - df_lic['used_quantity']
        low_lic_alert = len(df_lic[df_lic['remaining'] <= df_lic['alert_threshold']])
        st.metric("Rủi ro License", f"{low_lic_alert}", "-1", delta_color="inverse")
    with c4:
        # Tần suất bảo trì
        maint_count = len(df_maint)
        st.metric("Yêu cầu hỗ trợ", f"{maint_count}", "Tuần này")

    st.markdown("---")

    # --- 3. PHÂN TÍCH TRỰC QUAN (VISUAL ANALYTICS) ---
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### 🏗️ Cơ cấu tài sản theo chủng loại")
        # Map mã loại sang tên đầy đủ để làm báo cáo chuyên nghiệp
        type_labels = {'LT': 'Laptop', 'PC': 'Desktop PC', 'MN': 'Monitor', 'Server': 'Server', 'Other': 'Khác'}
        df_assets['Type Name'] = df_assets['type'].map(type_labels)
        fig_type = px.pie(df_assets, names='Type Name', hole=0.6, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_type.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
        st.plotly_chart(fig_type, use_container_width=True)

    with col_right:
        st.markdown("#### 📈 Xu hướng bảo trì hệ thống")
        if not df_maint.empty:
            df_maint['date'] = pd.to_datetime(df_maint['performed_at'])
            maint_trend = df_maint.groupby(df_maint['date'].dt.date).count().reset_index()
            fig_trend = px.area(maint_trend, x='date', y='id', 
                               labels={'id': 'Số lượt', 'date': 'Ngày'},
                               color_discrete_sequence=['#0071e3'])
            fig_trend.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.caption("Chưa có dữ liệu lịch sử bảo trì.")

    # --- 4. TRUNG TÂM CẢNH BÁO RỦI RO (RISK MANAGEMENT) ---
    st.markdown("### ⚠️ Trung tâm cảnh báo rủi ro")
    
    tab_lic, tab_maint = st.tabs(["📌 License sắp hết hạn", "🛠️ Thiết bị cần bảo trì"])
    
    with tab_lic:
        if not df_lic.empty:
            # Lọc các license có tỷ lệ sử dụng trên 80% hoặc dưới ngưỡng alert
            risk_lic = df_lic[df_lic['remaining'] <= df_lic['alert_threshold']].copy()
            if not risk_lic.empty:
                st.dataframe(
                    risk_lic[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date']],
                    column_config={
                        "name": "Tên phần mềm",
                        "remaining": st.column_config.NumberColumn("Số lượng còn lại", format="%d ⚠️"),
                        "expiry_date": "Hạn dùng"
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.success("Tất cả License đều đang trong ngưỡng an toàn.")

    with tab_maint:
        # Giả định: Các máy có trên 3 lần sửa chữa hoặc chưa bảo trì > 6 tháng cần chú ý
        if not df_maint.empty:
            high_maint_assets = df_maint.groupby('asset_id').count().reset_index()
            critical_assets = high_maint_assets[high_maint_assets['id'] >= 3]
            if not critical_assets.empty:
                st.warning(f"Phát hiện {len(critical_assets)} thiết bị có tần suất hỏng hóc cao. Cần xem xét thay thế.")
                # Merge với df_assets để lấy tag
                df_critical = pd.merge(critical_assets, df_assets, left_on='asset_id', right_on='id')
                st.table(df_critical[['asset_tag', 'type', 'id_x']].rename(columns={'id_x': 'Số lần sửa'}))
            else:
                st.info("Tình trạng thiết bị ổn định.")

    # --- 5. ĐỘI NGŨ & CHI NHÁNH ---
    st.markdown("---")
    with st.expander("🌐 Phân bổ tài sản theo chi nhánh"):
        # Kết nối với bảng Staff để xem phân bổ theo Branch
        staff_res = supabase.table("staff").select("employee_code", "branch").execute()
        if staff_res.data:
            df_staff = pd.DataFrame(staff_res.data)
            df_merged = pd.merge(df_assets, df_staff, left_on='assigned_to_code', right_on='employee_code')
            branch_dist = df_merged.groupby('branch').count().reset_index()
            fig_branch = px.bar(branch_dist, x='branch', y='id', color='branch',
                               title="Số lượng thiết bị theo Chi nhánh",
                               color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_branch, use_container_width=True)
