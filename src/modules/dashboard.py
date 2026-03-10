import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
    st.header("🏢 Enterprise Asset Intelligence")

    try:
        # 1. TẢI DỮ LIỆU
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("*").execute()
        res_lic = supabase.table("licenses").select("*").execute()
        res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        
        if df_assets.empty:
            st.warning("⚠️ Không có dữ liệu tài sản.")
            return

        # -------------------------------------------------
        # 2. XỬ LÝ CHUẨN HÓA MÃ NHÂN VIÊN (SỬA LỖI TRIỆT ĐỂ)
        # -------------------------------------------------
        # Chuyển tất cả về chuỗi, viết hoa và xóa khoảng trắng thừa
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).str.strip()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Thực hiện Merge
        df_merged = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # CƯỠNG BỨC TẠO CỘT: Nếu sau merge vẫn không có full_name (do staff trống)
        if 'full_name' not in df_merged.columns:
            df_merged['full_name'] = "N/A"
        if 'branch' not in df_merged.columns:
            df_merged['branch'] = "N/A"
        if 'department' not in df_merged.columns:
            df_merged['department'] = "N/A"

        # Điền giá trị mặc định cho các dòng không khớp (Unassigned)
        df_merged['full_name'] = df_merged['full_name'].fillna("Kho tổng / Chưa cấp")
        df_merged['branch'] = df_merged['branch'].fillna("Văn phòng")
        df_merged['department'] = df_merged['department'].fillna("Hạ tầng")

        # -------------------------------------------------
        # 3. BỘ LỌC TOÀN CỤC (SIDEBAR)
        # -------------------------------------------------
        with st.sidebar:
            st.divider()
            st.subheader("🛠️ Bộ lọc dữ liệu")
            
            # Filter Chi nhánh (Branch)
            branches = ["Tất cả"] + sorted(df_merged['branch'].unique().tolist())
            sel_branch = st.selectbox("Chi nhánh", branches)
            
            # Filter Phòng ban (Department)
            depts = ["Tất cả"] + sorted(df_merged['department'].unique().tolist())
            sel_dept = st.selectbox("Phòng ban", depts)
            
            # Filter Loại máy (Category - nếu có)
            asset_types = ["Tất cả"]
            if 'category' in df_merged.columns:
                asset_types += sorted(df_merged['category'].unique().tolist())
            sel_type = st.selectbox("Loại tài sản", asset_types)

        # -------------------------------------------------
        # 4. TÌM KIẾM & DRILL-DOWN (TIÊU CHÍ 2 & 3)
        # -------------------------------------------------
        search_query = st.text_input("🔍 Tìm nhanh Asset hoặc Nhân sự", placeholder="Nhập Asset Tag, Tên nhân viên...")

        # Áp dụng Filter
        df_filtered = df_merged.copy()
        if sel_branch != "Tất cả":
            df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_type != "Tất cả":
            df_filtered = df_filtered[df_filtered['category'] == sel_type]
            
        if search_query:
            df_filtered = df_filtered[
                df_filtered['asset_tag'].str.contains(search_query, case=False, na=False) | 
                df_filtered['full_name'].str.contains(search_query, case=False, na=False) |
                df_filtered['assigned_to_code'].str.contains(search_query, case=False, na=False)
            ]

        # -------------------------------------------------
        # 5. GỌI AI ENGINE & HIỂN THỊ
        # -------------------------------------------------
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)
        
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # KPI Metrics
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Máy đang hiển thị", len(df_filtered))
        m2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        m3.metric("🔑 Lỗi License", metrics.get("license_alerts", 0))
        m4.metric("🛠️ MTTR (Avg)", metrics.get("mttr", "N/A"))

        # Visual Charts & Drill-down
        st.markdown("---")
        c_left, c_right = st.columns([6, 4])
        
        with c_left:
            st.subheader("📊 Phân bổ rủi ro hệ thống")
            fig = px.pie(df_ai, names='risk_level', hole=0.5,
                         color='risk_level', color_discrete_map={
                             "🔴 Nguy cấp": "#FF4B4B", "🟠 Cao": "#FFA500", "🟢 Thấp": "#28A745"
                         })
            st.plotly_chart(fig, use_container_width=True)

        with c_right:
            st.subheader("📋 Danh sách Drill-down")
            st.caption("Dữ liệu lọc theo Search & Sidebar bên trái")
            st.dataframe(
                df_ai[['asset_tag', 'full_name', 'risk_level', 'department']].rename(columns={
                    'asset_tag': 'Mã máy', 'full_name': 'Người dùng', 
                    'risk_level': 'Mức độ', 'department': 'Phòng ban'
                }), 
                use_container_width=True, hide_index=True, height=400
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

def render_usage_details(supabase):
    """Đồng bộ Tab 5 sử dụng chung logic an toàn"""
    render_dashboard(supabase)
