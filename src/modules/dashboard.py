import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
    st.header("🏢 Enterprise Asset Intelligence")

    # 1. TẢI DỮ LIỆU GỐC
    df_assets = pd.DataFrame(supabase.table("assets").select("*").execute().data)
    df_staff = pd.DataFrame(supabase.table("staff").select("*").execute().data)
    df_lic = pd.DataFrame(supabase.table("licenses").select("*").execute().data)
    df_maint = pd.DataFrame(supabase.table("maintenance_log").select("*").execute().data)

    # 2. GLOBAL SEARCH (Tiêu chí 3)
    search_query = st.text_input("🔍 Tìm nhanh Asset (Mã máy, Tên nhân viên...)", placeholder="Nhập mã máy hoặc tên...")

    # 3. GLOBAL FILTERS TRONG SIDEBAR (Tiêu chí 1)
    with st.sidebar:
        st.divider()
        st.subheader("🛠️ Bộ lọc toàn cục")
        branch_list = ["Tất cả"] + sorted(list(df_staff['branch'].dropna().unique()))
        sel_branch = st.selectbox("Chi nhánh", branch_list)
        
        dept_list = ["Tất cả"] + sorted(list(df_staff['department'].dropna().unique()))
        sel_dept = st.selectbox("Phòng ban", dept_list)

    # 4. LOGIC LỌC DỮ LIỆU TRƯỚC KHI ĐƯA VÀO AI ENGINE
    df_filtered = pd.merge(df_assets, df_staff[['employee_code', 'full_name', 'department', 'branch']], 
                           left_on='assigned_to_code', right_on='employee_code', how='left')
    
    if sel_branch != "Tất cả":
        df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
    if sel_dept != "Tất cả":
        df_filtered = df_filtered[df_filtered['department'] == sel_dept]
    if search_query:
        df_filtered = df_filtered[
            df_filtered['asset_tag'].str.contains(search_query, case=False) | 
            df_filtered['full_name'].str.contains(search_query, case=False, na=False)
        ]

    # 5. GỌI AI ENGINE VỚI DỮ LIỆU ĐÃ LỌC
    metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
        df_filtered, df_maint, df_lic, df_staff
    )

    # 6. HIỂN THỊ KPI & BIỂU ĐỒ (Drill-down cơ bản - Tiêu chí 2)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Máy đang lọc", len(df_filtered))
    m2.metric("🚨 Nguy cấp", metrics["critical_assets"])
    m3.metric("🔑 Cảnh báo License", metrics["license_alerts"])
    m4.metric("🛠️ MTTR", metrics["mttr"])

    # Biểu đồ và Drill-down list
    col_chart, col_list = st.columns([1, 1])
    with col_chart:
        st.subheader("Phân bổ rủi ro")
        fig = px.pie(df_ai, names='risk_level', color='risk_level', hole=0.4,
                     color_discrete_map={"🔴 Nguy cấp": "#FF4B4B", "🟠 Cao": "#FFA500", "🟢 Thấp": "#28A745"})
        st.plotly_chart(fig, use_container_width=True)

    with col_list:
        st.subheader("Danh sách Drill-down")
        st.caption("Hiển thị dựa trên bộ lọc phía trên")
        st.dataframe(
            df_ai[['asset_tag', 'full_name', 'risk_level']].rename(columns={
                'asset_tag': 'Mã máy', 'full_name': 'Người dùng', 'risk_level': 'Mức độ'
            }), use_container_width=True, hide_index=True, height=300
        )
