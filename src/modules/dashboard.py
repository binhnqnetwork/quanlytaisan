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

        # 2. TIỀN XỬ LÝ (TRƯỚC KHI GỌI AI ENGINE)
        # Giữ nguyên để AI Engine nhận dữ liệu sạch
        for df, col in [(df_assets, 'assigned_to_code'), (df_staff, 'employee_code')]:
            df[col] = df[col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df[col] = df[col].replace(['nan', 'None', 'null', '<NA>', ''], np.nan)

        # 3. GỌI AI ENGINE (LUỒNG XỬ LÝ CHÍNH)
        # Lưu ý: df_ai bây giờ đã là bảng ĐÃ GỘP NHÓM (Grouped)
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_assets, df_maint, df_lic, df_staff
        )

        # -------------------------------------------------
        # 4. SIDEBAR & BỘ LỌC (Cập nhật tên cột mới)
        # -------------------------------------------------
        with st.sidebar:
            st.header("🎯 Bộ lọc dữ liệu")
            
            # Cột 'branch' và 'department' vẫn giữ nguyên tên từ AI Engine
            branches = ["Tất cả"] + sorted(df_ai['branch'].dropna().unique().tolist())
            sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")

            depts = ["Tất cả"] + sorted(df_ai['department'].dropna().unique().tolist())
            sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")

        # 5. LOGIC LỌC DỮ LIỆU HIỂN THỊ
        df_display = df_ai.copy()
        if sel_branch != "Tất cả":
            df_display = df_display[df_display['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_display = df_display[df_display['department'] == sel_dept]

        # -------------------------------------------------
        # 6. TRA CỨU NHANH (Sửa lỗi: dùng tên cột mới sau Groupby)
        # -------------------------------------------------
        search = st.text_input("🔍 Tra cứu nhanh", placeholder="Mã máy hoặc tên nhân sự...", key=f"{key_prefix}_se")
        if search:
            # Sử dụng cột 'Mã máy' và 'Nhân viên sở hữu' thay vì asset_tag và full_name
            df_display = df_display[
                df_display['Mã máy'].str.contains(search, case=False, na=False) |
                df_display['Nhân viên sở hữu'].str.contains(search, case=False, na=False)
            ]

        # 7. KPI DASHBOARD
        m1, m2, m3, m4 = st.columns(4)
        # Tính tổng máy dựa trên cột 'Số lượng' (vì mỗi dòng giờ là 1 người)
        total_machines = df_display['Số lượng'].sum() if 'Số lượng' in df_display.columns else len(df_display)
        
        m1.metric("Tổng thiết bị", f"{total_machines} máy")
        m2.metric("👤 Nhân sự", f"{len(df_display)} người") # Số dòng tương ứng số người
        m3.metric("🔑 Bản quyền", metrics.get("license_alerts", 0))
        m4.metric("⚙️ MTTR", f"{metrics.get('mttr', 0)}h")

        st.markdown("---")
        st.markdown("### 📋 Danh sách Quản lý Tài sản (Gộp theo nhân sự)")
        
        # 8. HIỂN THỊ BẢNG (Dữ liệu đã được chuẩn hóa tên từ AI Engine)
        # Chúng ta không cần gán lại tên cột nữa vì AI Engine đã làm rồi
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True, 
            height=500
        )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
