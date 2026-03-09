import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def render_dashboard(supabase):
    # --- 1. GIAO DIỆN & STYLE ---
    st.markdown("""
        <style>
        .stMetric { background: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .dashboard-card { background: white; padding: 20px; border-radius: 16px; border: 1px solid #d2d2d7; margin-bottom: 20px; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 style="font-weight: 700; color: #1d1d1f;">📊 AI Strategic Hub - Enterprise Analytics</h1>', unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU AN TOÀN ---
    try:
        assets_res = supabase.table("assets").select("*").execute()
        lic_res = supabase.table("licenses").select("*").execute()
        maint_res = supabase.table("maintenance_log").select("*").execute()
        staff_res = supabase.table("staff").select("employee_code", "branch").execute()

        df_assets = pd.DataFrame(assets_res.data) if assets_res.data else pd.DataFrame()
        df_lic = pd.DataFrame(lic_res.data) if lic_res.data else pd.DataFrame()
        df_maint = pd.DataFrame(maint_res.data) if maint_res.data else pd.DataFrame()
        df_staff = pd.DataFrame(staff_res.data) if staff_res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    if df_assets.empty:
        st.info("Chưa có dữ liệu thiết bị để phân tích Dashboard.")
        return

    # --- 3. TOP-LEVEL KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        total_assets = len(df_assets)
        st.metric("Tổng thiết bị", f"{total_assets}", "Toàn hệ thống")
    with c2:
        in_use = len(df_assets[df_assets['status'] == "Đang sử dụng"])
        usage_rate = (in_use / total_assets * 100) if total_assets > 0 else 0
        st.metric("Tỷ lệ sử dụng", f"{usage_rate:.1f}%", f"{in_use} máy")
    with c3:
        # Tính rủi ro License (Remaining <= Threshold)
        df_lic['remaining'] = df_lic['total_quantity'] - df_lic['used_quantity']
        low_lic_alert = len(df_lic[df_lic['remaining'] <= df_lic['alert_threshold']])
        st.metric("Rủi ro License", f"{low_lic_alert}", "Cần gia hạn", delta_color="inverse")
    with c4:
        maint_count = len(df_maint)
        st.metric("Tổng lượt bảo trì", f"{maint_count}", "Lịch sử")

    st.markdown("---")

    # --- 4. PHÂN TÍCH TRỰC QUAN (VISUAL ANALYTICS) ---
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("#### 🏗️ Cơ cấu tài sản")
        type_labels = {'LT': 'Laptop', 'PC': 'Desktop PC', 'MN': 'Monitor', 'Server': 'Server', 'Other': 'Khác'}
        df_assets['Type Label'] = df_assets['type'].map(type_labels).fillna('Khác')
        fig_pie = px.pie(df_assets, names='Type Label', hole=0.5,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_layout(margin=dict(t=20, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        st.markdown("#### 📈 Xu hướng bảo trì")
        if not df_maint.empty:
            df_trend = df_maint.copy()
            df_trend['maint_date'] = pd.to_datetime(df_trend['performed_at']).dt.date
            trend_data = df_trend.groupby('maint_date').size().reset_index(name='Count')
            
            fig_trend = px.line(trend_data, x='maint_date', y='Count', markers=True,
                               labels={'Count': 'Số lượt', 'maint_date': 'Ngày'},
                               color_discrete_sequence=['#0071e3'])
            fig_trend.update_layout(margin=dict(t=20, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.caption("Chưa có dữ liệu bảo trì.")

    # --- 5. TRUNG TÂM QUẢN TRỊ RỦI RO ---
    st.markdown("### ⚠️ Trung tâm cảnh báo rủi ro")
    tab_lic, tab_maint, tab_branch = st.tabs(["📌 License", "🛠️ Thiết bị", "🌐 Chi nhánh"])
    
    with tab_lic:
        if not df_lic.empty:
            risk_lic = df_lic[df_lic['remaining'] <= df_lic['alert_threshold']].copy()
            if not risk_lic.empty:
                st.warning(f"Có {len(risk_lic)} phần mềm sắp hết hoặc quá hạn bản quyền.")
                st.dataframe(
                    risk_lic[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date']],
                    column_config={
                        "name": "Tên phần mềm",
                        "remaining": "Còn lại",
                        "expiry_date": st.column_config.DateColumn("Ngày hết hạn")
                    },
                    use_container_width=True, hide_index=True
                )
            else:
                st.success("Tình trạng License ổn định.")

    with tab_maint:
        if not df_maint.empty:
            # Tìm các máy sửa trên 3 lần
            maint_counts = df_maint.groupby('asset_id').size().reset_index(name='Count')
            critical_ids = maint_counts[maint_counts['Count'] >= 3]
            
            if not critical_ids.empty:
                df_critical = pd.merge(critical_ids, df_assets, left_on='asset_id', right_on='id')
                st.error(f"Phát hiện {len(df_critical)} thiết bị có tần suất hỏng hóc cao (≥3 lần).")
                st.table(df_critical[['asset_tag', 'Type Label', 'Count']].rename(columns={'Count': 'Số lần sửa'}))
            else:
                st.info("Chưa có thiết bị nào cần thay thế khẩn cấp.")

    with tab_branch:
        if not df_staff.empty:
            # Gộp dữ liệu an toàn
            df_asset_branch = pd.merge(
                df_assets[['id', 'assigned_to_code']], 
                df_staff[['employee_code', 'branch']], 
                left_on='assigned_to_code', 
                right_on='employee_code'
            )
            if not df_asset_branch.empty:
                branch_dist = df_asset_branch.groupby('branch').size().reset_index(name='Số lượng')
                fig_branch = px.bar(branch_dist, x='branch', y='Số lượng', color='branch',
                                   color_discrete_sequence=px.colors.qualitative.Set2)
                st.plotly_chart(fig_branch, use_container_width=True)
            else:
                st.write("Chưa có thiết bị nào được cấp phát theo chi nhánh.")

    # --- 6. FOOTER CHIẾN LƯỢC ---
    with st.expander("📝 Ghi chú báo cáo"):
        st.markdown(f"""
        - **Dữ liệu cập nhật lúc:** {datetime.now().strftime('%H:%M %d/%m/%Y')}
        - **Tỷ lệ sẵn sàng:** Dựa trên số lượng thiết bị trạng thái 'Trong kho'.
        - **Rủi ro License:** Được tính dựa trên ngưỡng cảnh báo thiết lập tại Tab License.
        """)
