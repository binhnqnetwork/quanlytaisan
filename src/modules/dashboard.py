import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="main"):
    st.markdown("### 🏢 Hệ Thống Quản Trị Tài Sản Doanh Nghiệp")

    try:
        # 1. TRUY XUẤT DỮ LIỆU
        with st.spinner("Đang đồng bộ dữ liệu hệ thống..."):
            res_assets = supabase.table("assets").select("*").execute()
            res_staff = supabase.table("staff").select("*").execute()
            res_lic = supabase.table("licenses").select("*").execute()
            res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)

        if df_assets.empty or df_staff.empty:
            st.warning("⚠️ Dữ liệu nền chưa sẵn sàng. Vui lòng kiểm tra bảng Assets và Staff.")
            return

        # -------------------------------------------------
        # -------------------------------------------------
        # 2. CHUẨN HÓA DỮ LIỆU (OPTIMIZED)
        # -------------------------------------------------

        # Hàm nội bộ để làm sạch mã: xóa .0, xóa 0 ở đầu, xóa khoảng trắng
        def clean_and_strip_zeros(s):
            if pd.isna(s): return pd.NA
            # Chuyển về string, xóa .0 (nếu có do float), xóa khoảng trắng
            s = str(s).split('.')[0].strip()
            # Xóa các số 0 ở đầu (Regex của bạn rất tốt)
            s = s.lstrip('0')
            return s if s != "" else "0" # Tránh trường hợp mã là '000'

        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].apply(clean_and_strip_zeros).astype("string")
        df_staff['employee_code'] = df_staff['employee_code'].apply(clean_and_strip_zeros).astype("string")

        # -------------------------------------------------
        # MERGE DỮ LIỆU (Đảm bảo không bị trùng cột)
        # -------------------------------------------------
        # Dùng validate='m:1' để đảm bảo 1 tài sản chỉ thuộc về tối đa 1 nhân viên
        df_main = pd.merge(
            df_assets,
            df_staff[['employee_code', 'full_name', 'department', 'branch']],
            left_on='assigned_to_code',
            right_on='employee_code',
            how='left'
        )

        # -------------------------------------------------
        # PHÂN LOẠI HIỂN THỊ
        # -------------------------------------------------

        mask_in_stock = df_main['assigned_to_code'].isna()

        df_main.loc[mask_in_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
        df_main.loc[mask_in_stock, 'department'] = 'Lưu kho'
        df_main.loc[mask_in_stock, 'branch'] = 'Toàn quốc'

        mask_error = df_main['full_name'].isna() & df_main['assigned_to_code'].notna()

        df_main.loc[mask_error, 'full_name'] = (
            '⚠️ Không tìm thấy NV: ' + df_main['assigned_to_code'].astype(str)
        )

        # -------------------------------------------------
        # 3. SIDEBAR & BỘ LỌC
        # -------------------------------------------------

        with st.sidebar:
            st.image("https://cdn-icons-png.flaticon.com/512/1063/1063376.png", width=80)
            st.header("🎯 Bộ lọc dữ liệu")

            with st.expander("📍 Vị trí & Phòng ban", expanded=True):

                branches = ["Tất cả"] + sorted(
                    [str(x) for x in df_main['branch'].dropna().unique()]
                )

                sel_branch = st.selectbox(
                    "Chi nhánh", branches, key=f"{key_prefix}_br"
                )

                depts = ["Tất cả"] + sorted(
                    [str(x) for x in df_main['department'].dropna().unique()]
                )

                sel_dept = st.selectbox(
                    "Phòng ban", depts, key=f"{key_prefix}_de"
                )

            with st.expander("🖥️ Loại thiết bị", expanded=True):

                types = ["Tất cả"] + sorted(
                    [str(x) for x in df_main['type'].dropna().unique()]
                )

                sel_type = st.selectbox(
                    "Loại tài sản", types, key=f"{key_prefix}_ty"
                )

        # -------------------------------------------------
        # 4. LOGIC LỌC DỮ LIỆU
        # -------------------------------------------------

        df_filtered = df_main.copy()

        if sel_branch != "Tất cả":
            df_filtered = df_filtered[df_filtered['branch'] == sel_branch]

        if sel_dept != "Tất cả":
            df_filtered = df_filtered[df_filtered['department'] == sel_dept]

        if sel_type != "Tất cả":
            df_filtered = df_filtered[df_filtered['type'] == sel_type]

        # -------------------------------------------------
        # 5. AI ENGINE
        # -------------------------------------------------

        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered,
            df_maint,
            df_lic,
            df_staff
        )

        # -------------------------------------------------
        # 6. SEARCH
        # -------------------------------------------------

        search = st.text_input(
            "🔍 Tra cứu nhanh tài sản",
            placeholder="Nhập mã máy hoặc tên nhân viên...",
            key=f"{key_prefix}_se"
        )

        if search:

            df_ai = df_ai[
                df_ai['asset_tag'].str.contains(search, case=False, na=False)
                | df_ai['full_name'].str.contains(search, case=False, na=False)
            ]

        # -------------------------------------------------
        # KPI
        # -------------------------------------------------

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Tổng thiết bị", f"{len(df_filtered)} máy")

        m2.metric(
            "🚨 Nguy cấp",
            metrics.get("critical_assets", 0),
            delta="Rủi ro cao",
            delta_color="inverse"
        )

        m3.metric(
            "🔑 Bản quyền",
            metrics.get("license_alerts", 0),
            delta="Sắp hết hạn"
        )

        m4.metric(
            "⚙️ MTTR",
            f"{metrics.get('mttr', 0)}h",
            help="Thời gian trung bình để sửa chữa"
        )

        st.markdown("---")

        # -------------------------------------------------
        # CHARTS
        # -------------------------------------------------

        c_left, c_right = st.columns(2)

        with c_left:

            st.subheader("📊 Phân bổ Rủi ro (AI)")

            fig_pie = px.pie(
                df_ai,
                names='risk_level',
                hole=0.5,
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#EF5350",
                    "🟠 Cao": "#FFA726",
                    "🟡 Trung bình": "#FFEE58",
                    "🟢 Thấp": "#66BB6A"
                }
            )

            st.plotly_chart(fig_pie, use_container_width=True)

        with c_right:

            st.subheader("🏢 Phân bổ theo Chi nhánh")

            branch_counts = (
                df_ai['branch']
                .value_counts()
                .rename_axis('branch')
                .reset_index(name='count')
            )

            fig_bar = px.bar(
                branch_counts,
                x='count',
                y='branch',
                orientation='h',
                color='branch'
            )

            st.plotly_chart(fig_bar, use_container_width=True)

        # -------------------------------------------------
        # BẢNG CHI TIẾT
        # -------------------------------------------------

        st.markdown("### 📋 Danh sách Drill-down Chi tiết")

        def color_risk(val):

            if pd.isna(val):
                return ""

            color = (
                '#66BB6A' if 'Thấp' in val
                else '#FFEE58' if 'Trung bình' in val
                else '#FFA726' if 'Cao' in val
                else '#EF5350'
            )

            return f'color: {color}; font-weight: bold'

        display_df = df_ai[
            ['asset_tag', 'full_name', 'department', 'branch', 'risk_level']
        ].copy()

        display_df.columns = [
            'Mã máy',
            'Nhân viên sở hữu',
            'Phòng ban',
            'Chi nhánh',
            'Mức độ rủi ro'
        ]

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
