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
            st.warning("⚠️ Dữ liệu nền chưa sẵn sàng.")
            return

        # -------------------------------------------------
        # 2. CHUẨN HÓA DỮ LIỆU (SỬ DỤNG KIỂU SỐ NGUYÊN)
        # -------------------------------------------------
        
        # Chuyển đổi mã về kiểu số nguyên (Int64 cho phép chứa giá trị Null)
        # Điều này giúp '10044' (str) khớp hoàn toàn với 10044 (int)
        df_assets['assigned_to_code'] = pd.to_numeric(df_assets['assigned_to_code'], errors='coerce').astype('Int64')
        df_staff['employee_code'] = pd.to_numeric(df_staff['employee_code'], errors='coerce').astype('Int64')

        # -------------------------------------------------
        # 3. MERGE DỮ LIỆU
        # -------------------------------------------------

        df_main = pd.merge(
            df_assets,
            df_staff[['employee_code', 'full_name', 'department', 'branch']],
            left_on='assigned_to_code',
            right_on='employee_code',
            how='left'
        )

        # -------------------------------------------------
        # 4. PHÂN LOẠI HIỂN THỊ
        # -------------------------------------------------

        # Case 1: Máy trong kho (Không có mã gán)
        mask_in_stock = df_main['assigned_to_code'].isna()
        df_main.loc[mask_in_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
        df_main.loc[mask_in_stock, 'department'] = 'Hạ tầng'
        df_main.loc[mask_in_stock, 'branch'] = 'Toàn quốc'

        # Case 2: Có mã nhưng không tìm thấy nhân viên (Lỗi khớp mã)
        mask_error = df_main['full_name'].isna() & df_main['assigned_to_code'].notna()
        df_main.loc[mask_error, 'full_name'] = '⚠️ Mã không tồn tại: ' + df_main['assigned_to_code'].astype(str)

        # -------------------------------------------------
        # 5. SIDEBAR & LOGIC LỌC (GIỮ NGUYÊN NHƯ CŨ)
        # -------------------------------------------------
        # ... (Phần code lọc dữ liệu và Sidebar giữ nguyên)
        
        # [Đoạn này copy lại phần UI của bạn...]
        
        with st.sidebar:
            st.header("🎯 Bộ lọc dữ liệu")
            with st.expander("📍 Vị trí & Phòng ban", expanded=True):
                branches = ["Tất cả"] + sorted([str(x) for x in df_main['branch'].dropna().unique()])
                sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")
                depts = ["Tất cả"] + sorted([str(x) for x in df_main['department'].dropna().unique()])
                sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")

        df_filtered = df_main.copy()
        if sel_branch != "Tất cả": df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả": df_filtered = df_filtered[df_filtered['department'] == sel_dept]

        # 6. AI ENGINE
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # 7. HIỂN THỊ KPI & BẢNG
        st.subheader("📋 Danh sách Drill-down Chi tiết")
        
        display_df = df_ai[['asset_tag', 'full_name', 'department', 'branch', 'risk_level']].copy()
        display_df.columns = ['Mã máy', 'Nhân viên sở hữu', 'Phòng ban', 'Chi nhánh', 'Mức độ rủi ro']

        st.dataframe(display_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Lỗi: {str(e)}")
