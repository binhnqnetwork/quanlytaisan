import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="main"):
    st.markdown(f"### 🏢 Hệ Thống Quản Trị Tài Sản Doanh Nghiệp")

    try:
        # 1. TRUY XUẤT DỮ LIỆU
        with st.spinner("Đang đồng bộ dữ liệu hệ thống..."):
            res_assets = supabase.table("assets").select("*").execute()
            res_staff = supabase.table("staff").select("*").execute()
            res_lic = supabase.table("licenses").select("*").execute()
            res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        
        if df_assets.empty or df_staff.empty:
            st.warning("⚠️ Dữ liệu nền chưa sẵn sàng. Vui lòng kiểm tra bảng Assets và Staff.")
            return

        # -------------------------------------------------
        # 2. CHUẨN HÓA DỮ LIỆU & MERGE (LOGIC CHỐNG SAI LỆCH)
        # -------------------------------------------------
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).replace(['None', 'nan', '<NA>', ''], None).str.strip()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Map dữ liệu nhân sự
        df_main = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # Xử lý các dòng chưa gán nhân viên (Máy trong kho)
        mask_stock = df_main['assigned_to_code'].isna()
        df_main.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
        df_main.loc[mask_stock, 'department'] = 'Lưu kho'
        df_main.loc[mask_stock, 'branch'] = 'Chưa gán'

        # -------------------------------------------------
        # 3. SIDEBAR: ĐIỀU KHIỂN & BỘ LỌC THÔNG MINH
        # -------------------------------------------------
        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=80)
            st.header("🎯 Bộ lọc dữ liệu")
            
            with st.expander("📍 Vị trí & Phòng ban", expanded=True):
                branches = ["Tất cả"] + sorted([x for x in df_main['branch'].unique() if pd.notna(x)])
                sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")
                
                depts = ["Tất cả"] + sorted([x for x in df_main['department'].unique() if pd.notna(x)])
                sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")
            
            with st.expander("🖥️ Loại thiết bị", expanded=True):
                types = ["Tất cả"] + sorted([x for x in df_main['type'].unique() if pd.notna(x)])
                sel_type = st.selectbox("Loại tài sản", types, key=f"{key_prefix}_ty")

            st.markdown("---")
            # Nút xuất báo cáo chuyên nghiệp
            if st.button("📥 Xuất báo cáo Excel", use_container_width=True):
                st.toast("Đang khởi tạo file báo cáo...")

        # 4. LOGIC LỌC
        df_filtered = df_main.copy()
        if sel_branch != "Tất cả": df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả": df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_type != "Tất cả": df_filtered = df_filtered[df_filtered['type'] == sel_type]

        # -------------------------------------------------
        # 5. AI ENGINE & PHÂN TÍCH RỦI RO
        # -------------------------------------------------
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, pd.DataFrame(res_maint.data), pd.DataFrame(res_lic.data), df_staff
        )

        # Đảm bảo giữ lại metadata sau khi qua AI
        for col in ['full_name', 'department', 'branch']:
            if col not in df_ai.columns:
                df_ai = pd.merge(df_ai, df_main[['asset_tag', col]], on='asset_tag', how='left')

        # -------------------------------------------------
        # 6. GIAO DIỆN HIỂN THỊ CHUYÊN NGHIỆP
        # -------------------------------------------------
        
        # SEARCH BAR (Nổi bật)
        search = st.text_input("🔍 Tra cứu nhanh tài sản", placeholder="Nhập mã máy hoặc tên nhân viên...", key=f"{key_prefix}_se")
        if search:
            df_ai = df_ai[df_ai['asset_tag'].str.contains(search, case=False) | df_ai['full_name'].str.contains(search, case=False)]

        # KPI METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng thiết bị", f"{len(df_filtered)} máy")
        m2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0), delta="Rủi ro", delta_color="inverse")
        m3.metric("🔑 Bản quyền", metrics.get("license_alerts", 0), delta="Hết hạn")
        m4.metric("⚙️ Hiệu suất (MTTR)", f"{metrics.get('mttr', 0)}h")

        st.markdown("---")

        # CHI TIẾT PHÂN TÍCH (Charts)
        c_left, c_right = st.columns([5, 5])
        
        with c_left:
            st.subheader("📊 Phân bổ Rủi ro (AI)")
            fig_pie = px.pie(
                df_ai, names='risk_level', hole=0.5,
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#EF5350", "🟠 Cao": "#FFA726", 
                    "🟡 Trung bình": "#FFEE58", "🟢 Thấp": "#66BB6A"
                }
            )
            fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:
            st.subheader("🏢 Phân bổ theo Chi nhánh")
            # Biểu đồ cột ngang cho thấy chi nhánh nào đang sở hữu nhiều tài sản nhất
            branch_counts = df_ai['branch'].value_counts().reset_index()
            fig_bar = px.bar(branch_counts, x='count', y='branch', orientation='h', color='branch', color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_bar.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_bar, use_container_width=True)

        # DRILL-DOWN TABLE (Bản nâng cấp)
        st.markdown("### 📋 Danh sách Drill-down Chi tiết")
        
        # Styling cho bảng rực rỡ hơn
        def color_risk(val):
            color = '#66BB6A' if 'Thấp' in val else '#FFEE58' if 'Trung bình' in val else '#FFA726' if 'Cao' in val else '#EF5350'
            return f'color: {color}; font-weight: bold'

        display_df = df_ai[['asset_tag', 'full_name', 'department', 'branch', 'risk_level']].copy()
        display_df.columns = ['Mã máy', 'Nhân viên', 'Phòng ban', 'Chi nhánh', 'Mức độ rủi ro']

        st.dataframe(
            display_df.style.applymap(color_risk, subset=['Mức độ rủi ro']),
            use_container_width=True,
            hide_index=True,
            height=450
        )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

def render_usage_details(supabase):
    render_dashboard(supabase, key_prefix="usage_tab")
