import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="main"):
    """
    Hệ thống Dashboard đa năng. 
    Tham số key_prefix giúp tránh lỗi Duplicate Element ID.
    """
    st.markdown("### 🏢 Enterprise Asset Management System")

    try:
        # 1. FETCH DATA
        with st.spinner("Đang truy xuất dữ liệu..."):
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
        # 2. CHUẨN HÓA DỮ LIỆU & MAP NHÂN SỰ (PRO LOGIC)
        # -------------------------------------------------
        # Làm sạch mã gán (Chuyển các giá trị trống về None để Merge chuẩn xác)
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).replace(['None', 'nan', '<NA>', ''], None).str.strip()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Merge lấy thông tin nhân sự từ bảng Staff sang bảng Assets
        df_main = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # XỬ LÝ NHÃN CHO MÁY TRONG KHO (CHỈ FILLNA CHO DÒNG TRỐNG)
        mask_in_stock = df_main['assigned_to_code'].isna()
        df_main.loc[mask_in_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
        df_main.loc[mask_in_stock, 'department'] = 'Hạ tầng (Kho)'
        df_main.loc[mask_in_stock, 'branch'] = 'Chưa gán'

        # -------------------------------------------------
        # 3. FILTERS (Sử dụng key_prefix)
        # -------------------------------------------------
        with st.sidebar:
            st.header("🎯 Điều khiển Dashboard")
            
            # Lấy danh sách duy nhất và loại bỏ giá trị rác
            branches = ["Tất cả"] + sorted([x for x in df_main['branch'].unique() if pd.notna(x)])
            sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_branch")
            
            depts = ["Tất cả"] + sorted([x for x in df_main['department'].unique() if pd.notna(x)])
            sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_dept")
            
            types = ["Tất cả"] + sorted([x for x in df_main['type'].unique() if pd.notna(x)])
            sel_type = st.selectbox("Loại tài sản", types, key=f"{key_prefix}_type")

        # 4. SEARCH (Tìm theo mã máy hoặc tên người dùng)
        search_query = st.text_input("🔍 Tìm kiếm tài sản", 
                                     placeholder="Nhập mã máy hoặc tên nhân viên...", 
                                     key=f"{key_prefix}_search")

        # Áp dụng logic lọc dữ liệu
        df_filtered = df_main.copy()
        if sel_branch != "Tất cả": df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả": df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_type != "Tất cả": df_filtered = df_filtered[df_filtered['type'] == sel_type]
        
        if search_query:
            df_filtered = df_filtered[
                df_filtered['asset_tag'].str.contains(search_query, case=False, na=False) |
                df_filtered['full_name'].str.contains(search_query, case=False, na=False)
            ]

        # -------------------------------------------------
        # 5. AI ENGINE INTEGRATION & BẢO TOÀN DỮ LIỆU
        # -------------------------------------------------
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)

        # Gọi Engine AI để tính toán mức độ rủi ro
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # KIỂM TRA: Nếu AI Engine làm mất các cột Personel, ta map lại ngay
        for col in ['full_name', 'department', 'branch']:
            if col not in df_ai.columns:
                df_ai = pd.merge(df_ai, df_main[['asset_tag', col]], on='asset_tag', how='left')

        # -------------------------------------------------
        # 6. HIỂN THỊ (KPI & DRILL-DOWN)
        # -------------------------------------------------
        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng thiết bị", len(df_filtered))
        k2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        k3.metric("🔑 Bản quyền lỗi", metrics.get("license_alerts", 0))
        k4.metric("⚙️ MTTR (Avg)", metrics.get("mttr", "N/A"))

        st.markdown("---")
        col_pie, col_table = st.columns([4, 6]) 
        
        with col_pie:
            st.subheader("📊 Mức độ rủi ro (AI)")
            fig = px.pie(
                df_ai, names='risk_level', hole=0.6,
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#FF4B4B", "🟠 Cao": "#FFA500", 
                    "🟡 Trung bình": "#F0E68C", "🟢 Thấp": "#28A745"
                }
            )
            fig.update_layout(margin=dict(t=20, b=20, l=0, r=0), showlegend=True)
            st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_pie_chart")

        with col_table:
            st.subheader("📋 Danh sách Drill-down")
            
            # Hiển thị 5 cột thông tin cốt lõi
            display_df = df_ai[[
                'asset_tag', 
                'full_name', 
                'department', 
                'branch', 
                'risk_level'
            ]].copy()

            display_df.columns = ['Mã máy', 'Tên nhân viên', 'Phòng ban', 'Chi nhánh', 'Rủi ro']

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=400
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

def render_usage_details(supabase):
    render_dashboard(supabase, key_prefix="usage_tab")
