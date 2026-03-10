import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
    st.header("🏢 Enterprise Asset Intelligence")

    try:
        # 1. TẢI DỮ LIỆU GỐC
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("*").execute()
        res_lic = supabase.table("licenses").select("*").execute()
        res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)

        # KIỂM TRA AN TOÀN: Nếu bảng staff thiếu cột quan trọng, ta tự tạo cột rỗng để merge không lỗi
        required_staff_cols = ['employee_code', 'full_name', 'department', 'branch']
        for col in required_staff_cols:
            if col not in df_staff.columns:
                df_staff[col] = "N/A"

        # -------------------------------------------------
        # 2. XỬ LÝ MERGE AN TOÀN (Đây là nơi giải quyết dứt điểm lỗi)
        # -------------------------------------------------
        if not df_assets.empty:
            # Merge và ép kiểu dữ liệu để tránh lệch mã NV (ví dụ: string vs int)
            df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str)
            df_staff['employee_code'] = df_staff['employee_code'].astype(str)

            df_merged = pd.merge(
                df_assets, 
                df_staff[['employee_code', 'full_name', 'department', 'branch']], 
                left_on='assigned_to_code', 
                right_on='employee_code', 
                how='left'
            )
            
            # Đảm bảo 'full_name' tồn tại ngay cả khi merge thất bại hoàn toàn
            if 'full_name' not in df_merged.columns:
                df_merged['full_name'] = "Chưa xác định"
            
            df_merged['full_name'] = df_merged['full_name'].fillna("Kho tổng / Chưa cấp")
            df_merged['branch'] = df_merged['branch'].fillna("N/A")
            df_merged['department'] = df_merged['department'].fillna("N/A")
        else:
            st.warning("⚠️ Dữ liệu tài sản trống.")
            return

        # -------------------------------------------------
        # 3. GLOBAL FILTERS & SEARCH
        # -------------------------------------------------
        with st.sidebar:
            st.title("🎯 Bộ lọc Enterprise")
            # Sử dụng .get() hoặc kiểm tra trực tiếp để lấy list filter an toàn
            branches = ["Tất cả"] + sorted([b for b in df_merged['branch'].unique() if b and b != "N/A"])
            sel_branch = st.selectbox("Chi nhánh", branches)
            
            depts = ["Tất cả"] + sorted([d for d in df_merged['department'].unique() if d and d != "N/A"])
            sel_dept = st.selectbox("Phòng ban", depts)

        search_query = st.text_input("🔍 Tìm kiếm tài sản hoặc nhân sự...", placeholder="Nhập mã máy hoặc tên...")

        # Áp dụng Filter
        df_filtered = df_merged.copy()
        if sel_branch != "Tất cả":
            df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if search_query:
            # Dùng fillna để search không bị lỗi với dữ liệu null
            df_filtered = df_filtered[
                df_filtered['asset_tag'].str.contains(search_query, case=False, na=False) | 
                df_filtered['full_name'].str.contains(search_query, case=False, na=False)
            ]

        # -------------------------------------------------
        # 4. GỌI AI ENGINE & HIỂN THỊ
        # -------------------------------------------------
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Thiết bị hiển thị", len(df_filtered))
        k2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        k3.metric("🔑 Lỗi License", metrics.get("license_alerts", 0))
        k4.metric("🛠️ MTTR", metrics.get("mttr", "N/A"))

        st.markdown("---")
        c1, c2 = st.columns([6, 4])
        with c1:
            st.subheader("📊 Trạng thái Rủi ro")
            fig = px.pie(df_ai, names='risk_level', hole=0.4,
                         color='risk_level', color_discrete_map={"🔴 Nguy cấp": "#FF4B4B", "🟠 Cao": "#FFA500", "🟢 Thấp": "#28A745"})
            st.plotly_chart(fig, use_container_width=True)
        
        with c2:
            st.subheader("📋 Danh sách Drill-down")
            # Hiển thị bảng chi tiết cực kỳ an toàn
            display_cols = ['asset_tag', 'full_name', 'risk_level']
            st.dataframe(df_ai[display_cols].rename(columns={
                'asset_tag': 'Mã máy', 'full_name': 'Người dùng', 'risk_level': 'Mức độ'
            }), use_container_width=True, hide_index=True, height=400)

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
        st.info("Mẹo: Kiểm tra xem cột 'full_name' có thực sự nằm trong bảng 'staff' trên Supabase không.")

def render_usage_details(supabase):
    """Sử dụng lại logic render_dashboard cho Tab 5 nhưng ưu tiên bảng phẳng"""
    render_dashboard(supabase)
