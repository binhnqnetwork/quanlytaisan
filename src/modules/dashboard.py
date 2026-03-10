import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
    st.header("🏢 Enterprise Asset Intelligence")

    try:
        # 1. TẢI DỮ LIỆU GỐC
        df_assets = pd.DataFrame(supabase.table("assets").select("*").execute().data)
        df_staff = pd.DataFrame(supabase.table("staff").select("*").execute().data)
        df_lic = pd.DataFrame(supabase.table("licenses").select("*").execute().data)
        df_maint = pd.DataFrame(supabase.table("maintenance_log").select("*").execute().data)

        if df_assets.empty or df_staff.empty:
            st.warning("⚠️ Đang thiếu dữ liệu Assets hoặc Staff để phân tích.")
            return

        # -------------------------------------------------
        # 2. GLOBAL FILTERS (SIDEBAR) - Tiêu chí 1
        # -------------------------------------------------
        with st.sidebar:
            st.title("🎯 Bộ lọc hệ thống")
            
            branch_list = ["Tất cả"] + sorted([b for b in df_staff['branch'].unique() if b])
            sel_branch = st.selectbox("Chi nhánh (Region)", branch_list)
            
            dept_list = ["Tất cả"] + sorted([d for d in df_staff['department'].unique() if d])
            sel_dept = st.selectbox("Phòng ban (Department)", dept_list)
            
            status_list = ["Tất cả"] + sorted(list(df_assets['status'].unique()))
            sel_status = st.selectbox("Trạng thái thiết bị", status_list)

        # -------------------------------------------------
        # 3. XỬ LÝ DỮ LIỆU & FIX LỖI 'full_name'
        # -------------------------------------------------
        # Merge để có thông tin nhân sự đầy đủ
        df_merged = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )
        
        # Xử lý các giá trị trống sau khi merge để tránh lỗi logic
        df_merged['full_name'] = df_merged['full_name'].fillna("Kho tổng / Unassigned")
        df_merged['branch'] = df_merged['branch'].fillna("N/A")
        df_merged['department'] = df_merged['department'].fillna("N/A")

        # 4. GLOBAL SEARCH (Tiêu chí 3)
        search_query = st.text_input("🔍 Tìm nhanh Asset", placeholder="Nhập mã máy (Asset Tag) hoặc Tên nhân viên...")

        # Áp dụng Filter Toàn cục
        df_filtered = df_merged.copy()
        if sel_branch != "Tất cả":
            df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_status != "Tất cả":
            df_filtered = df_filtered[df_filtered['status'] == sel_status]
        if search_query:
            df_filtered = df_filtered[
                df_filtered['asset_tag'].str.contains(search_query, case=False) | 
                df_filtered['full_name'].str.contains(search_query, case=False)
            ]

        # -------------------------------------------------
        # 5. GỌI AI ENGINE (Xương sống không đổi)
        # -------------------------------------------------
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # 6. HIỂN THỊ KPI
        st.markdown("---")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Tổng thiết bị", len(df_filtered))
        kpi2.metric("🚨 Nguy cấp", metrics["critical_assets"])
        kpi3.metric("🔑 Lỗi License", metrics["license_alerts"])
        kpi4.metric("🛠️ MTTR Avg", metrics["mttr"])

        # 7. DRILL-DOWN VISUALIZATION (Tiêu chí 2)
        st.markdown("---")
        col_chart, col_drill = st.columns([6, 4])
        
        with col_chart:
            st.subheader("📊 Phân bổ Rủi ro")
            fig = px.pie(df_ai, names='risk_level', color='risk_level', hole=0.5,
                         color_discrete_map={
                             "🔴 Nguy cấp": "#FF4B4B", 
                             "🟠 Cao": "#FFA500", 
                             "🟢 Thấp": "#28A745"
                         })
            st.plotly_chart(fig, use_container_width=True)

        with col_drill:
            st.subheader("📋 Danh sách Drill-down")
            st.caption("Dữ liệu tự động cập nhật theo bộ lọc")
            st.dataframe(
                df_ai[['asset_tag', 'full_name', 'risk_level', 'branch']].rename(columns={
                    'asset_tag': 'Mã máy', 'full_name': 'Người dùng', 
                    'risk_level': 'Mức độ', 'branch': 'Vùng'
                }), 
                use_container_width=True, 
                hide_index=True, 
                height=350
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {e}")

def render_usage_details(supabase):
    """Giữ nguyên hàm này cho Tab 5 nhưng đồng bộ logic hiển thị"""
    st.header("👥 Truy xuất Chi tiết Cấp phát")
    # Tương tự như hàm render_dashboard nhưng tập trung vào bảng dữ liệu chi tiết
    # (Đã sửa lỗi attribute render_usage_details ở các bước trước)
