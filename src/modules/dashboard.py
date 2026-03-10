import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="main"):
    """
    Hệ thống Dashboard Quản trị Tài sản Doanh nghiệp - Bản hoàn thiện.
    Tối ưu cho dữ liệu thực tế từ Supabase (Fix lỗi Mismatch Data Type).
    """
    st.markdown("### 🏢 Hệ Thống Quản Trị Tài Sản Doanh Nghiệp")

    try:
        # 1. FETCH DATA (Đồng bộ dữ liệu thời gian thực)
        with st.spinner("Đang đồng bộ dữ liệu hệ thống..."):
            res_assets = supabase.table("assets").select("*").execute()
            res_staff = supabase.table("staff").select("*").execute()
            res_lic = supabase.table("licenses").select("*").execute()
            res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        
        if df_assets.empty or df_staff.empty:
            st.warning("⚠️ Dữ liệu nền chưa sẵn sàng. Vui lòng kiểm tra bảng Assets và Staff trên Supabase.")
            return

        # -------------------------------------------------
        # 2. CHUẨN HÓA DỮ LIỆU & MERGE (CHỐNG LỆCH ĐỊNH DẠNG)
        # -------------------------------------------------
        # Ép kiểu về String và làm sạch khoảng trắng để đảm bảo khớp nối 100%
        # Xử lý mã gán từ Assets
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).str.strip().replace(['None', 'nan', 'null', ''], None)
        
        # Xử lý mã nhân viên từ Staff
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Thực hiện Merge để lấy thông tin nhân sự sang bảng Assets
        df_main = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # XỬ LÝ NHÃN CHO MÁY CHƯA GÁN (KHO TỔNG)
        # Nếu không tìm thấy thông tin nhân viên (full_name is null)
        mask_unassigned = df_main['full_name'].isna()
        df_main.loc[mask_unassigned, 'full_name'] = '📦 Kho tổng / Hệ thống'
        df_main.loc[mask_unassigned, 'department'] = 'Hạ tầng (Kho)'
        df_main.loc[mask_unassigned, 'branch'] = 'Toàn quốc'

        # -------------------------------------------------
        # 3. SIDEBAR: ĐIỀU KHIỂN & BỘ LỌC CHUYÊN NGHIỆP
        # -------------------------------------------------
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=70)
            st.header("🎯 Trung tâm Điều khiển")
            
            with st.expander("📍 Vị trí & Tổ chức", expanded=True):
                branches = ["Tất cả"] + sorted([str(x) for x in df_main['branch'].unique() if pd.notna(x)])
                sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")
                
                depts = ["Tất cả"] + sorted([str(x) for x in df_main['department'].unique() if pd.notna(x)])
                sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")
            
            with st.expander("🖥️ Loại tài sản", expanded=True):
                types = ["Tất cả"] + sorted([str(x) for x in df_main['type'].unique() if pd.notna(x)])
                sel_type = st.selectbox("Phân loại", types, key=f"{key_prefix}_ty")

            st.markdown("---")
            if st.button("📥 Xuất báo cáo (CSV)", use_container_width=True):
                st.toast("Tính năng đang được khởi tạo...")

        # 4. ÁP DỤNG LOGIC LỌC
        df_filtered = df_main.copy()
        if sel_branch != "Tất cả": df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả": df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_type != "Tất cả": df_filtered = df_filtered[df_filtered['type'] == sel_type]

        # -------------------------------------------------
        # 5. AI ENGINE INTEGRATION (TÍNH TOÁN CHỈ SỐ)
        # -------------------------------------------------
        df_maint = pd.DataFrame(res_maint.data)
        df_lic = pd.DataFrame(res_lic.data)

        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # Bảo toàn Metadata nhân sự sau khi qua xử lý AI
        for col in ['full_name', 'department', 'branch']:
            if col not in df_ai.columns:
                df_ai = pd.merge(df_ai, df_main[['asset_tag', col]], on='asset_tag', how='left')

        # -------------------------------------------------
        # 6. GIAO DIỆN HIỂN THỊ CHI TIẾT
        # -------------------------------------------------
        
        # SEARCH BAR (Nổi bật phía trên)
        search_query = st.text_input("🔍 Tra cứu nhanh tài sản", 
                                     placeholder="Nhập mã máy hoặc tên nhân viên...", 
                                     key=f"{key_prefix}_search")
        if search_query:
            df_ai = df_ai[
                df_ai['asset_tag'].str.contains(search_query, case=False, na=False) |
                df_ai['full_name'].str.contains(search_query, case=False, na=False)
            ]

        # KPI METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng thiết bị", f"{len(df_filtered)}")
        m2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0), delta="Rủi ro cao", delta_color="inverse")
        m3.metric("🔑 Bản quyền", metrics.get("license_alerts", 0), delta="Hết hạn")
        m4.metric("⚙️ MTTR (Avg)", f"{metrics.get('mttr', 0)}h")

        st.markdown("---")

        # CHI TIẾT PHÂN TÍCH (Biểu đồ)
        c_left, c_right = st.columns([5, 5])
        
        with c_left:
            st.subheader("📊 Tỷ lệ Rủi ro hệ thống")
            fig_pie = px.pie(
                df_ai, names='risk_level', hole=0.55,
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#EF5350", "🟠 Cao": "#FFA726", 
                    "🟡 Trung bình": "#FFEE58", "🟢 Thấp": "#66BB6A"
                }
            )
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:
            st.subheader("🏢 Phân bổ theo Chi nhánh")
            branch_data = df_ai['branch'].value_counts().reset_index()
            fig_bar = px.bar(branch_data, x='count', y='branch', orientation='h', color='branch',
                             color_discrete_sequence=px.colors.qualitative.Safe)
            fig_bar.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)

        # TABLE DRILL-DOWN (Định dạng chuyên nghiệp)
        st.markdown("### 📋 Danh sách Drill-down Chi tiết")
        
        def apply_risk_color(val):
            if 'Nguy cấp' in val: return 'color: #EF5350; font-weight: bold'
            if 'Cao' in val: return 'color: #FFA726; font-weight: bold'
            if 'Trung bình' in val: return 'color: #FFEE58; font-weight: bold'
            return 'color: #66BB6A; font-weight: bold'

        display_df = df_ai[['asset_tag', 'full_name', 'department', 'branch', 'risk_level']].copy()
        display_df.columns = ['Mã máy', 'Nhân viên sở hữu', 'Phòng ban', 'Chi nhánh', 'Mức độ rủi ro']

        st.dataframe(
            display_df.style.applymap(apply_risk_color, subset=['Mức độ rủi ro']),
            use_container_width=True,
            hide_index=True,
            height=400
        )

    except Exception as e:
        st.error(f"❌ Hệ thống Dashboard gặp lỗi: {str(e)}")

def render_usage_details(supabase):
    render_dashboard(supabase, key_prefix="usage_tab")
