import streamlit as st
import pandas as pd
import numpy as np
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
        # 2. TIỀN XỬ LÝ (TRƯỚC KHI GỌI AI ENGINE)
        # -------------------------------------------------
        # Ép kiểu string và xử lý NA triệt để
        for df, col in [(df_assets, 'assigned_to_code'), (df_staff, 'employee_code')]:
            df[col] = df[col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df[col] = df[col].replace(['nan', 'None', 'null', '<NA>', ''], np.nan)

        # -------------------------------------------------
        # 3. GỌI AI ENGINE (LUỒNG XỬ LÝ CHÍNH)
        # -------------------------------------------------
        # Lưu ý: Truyền df_assets đã làm sạch vào đây
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_assets, df_maint, df_lic, df_staff
        )

        # -------------------------------------------------
        # 4. SIDEBAR & BỘ LỌC (Dùng df_ai để lấy list filter)
        # -------------------------------------------------
        with st.sidebar:
            st.header("🎯 Bộ lọc dữ liệu")
            
            # Sử dụng df_ai vì đây là dữ liệu ĐÃ MERGE tên nhân viên/phòng ban
            branches = ["Tất cả"] + sorted(df_ai['branch'].dropna().unique().tolist())
            sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")

            depts = ["Tất cả"] + sorted(df_ai['department'].dropna().unique().tolist())
            sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")

        # -------------------------------------------------
        # 5. LOGIC LỌC DỮ LIỆU HIỂN THỊ
        # -------------------------------------------------
        df_display = df_ai.copy()
        if sel_branch != "Tất cả":
            df_display = df_display[df_display['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_display = df_display[df_display['department'] == sel_dept]

        # 6. TRA CỨU NHANH
        search = st.text_input("🔍 Tra cứu nhanh", placeholder="Mã máy hoặc tên...", key=f"{key_prefix}_se")
        if search:
            df_display = df_display[
                df_display['asset_tag'].str.contains(search, case=False, na=False) |
                df_display['full_name'].str.contains(search, case=False, na=False)
            ]

        # 7. KPI DASHBOARD
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tổng thiết bị", f"{len(df_display)} máy")
        m2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        m3.metric("🔑 Bản quyền", metrics.get("license_alerts", 0))
        m4.metric("⚙️ MTTR", f"{metrics.get('mttr', 0)}h")

        st.markdown("---")
        st.markdown("### 📋 Danh sách Drill-down Chi tiết")
        
        # CHỈNH SỬA HIỂN THỊ CUỐI CÙNG
        final_table = df_display[['asset_tag', 'full_name', 'department', 'branch', 'risk_level']].copy()
        final_table.columns = ['Mã máy', 'Nhân viên sở hữu', 'Phòng ban', 'Chi nhánh', 'Mức độ rủi ro']

        st.dataframe(final_table, use_container_width=True, hide_index=True, height=500)

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
