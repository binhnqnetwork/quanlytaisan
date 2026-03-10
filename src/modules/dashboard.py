import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
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
        # 2. PRO DATA PREPARATION & NORMALIZATION
        # -------------------------------------------------
        # Chuẩn hóa mã nhân viên (Xử lý các mã có số 0 ở đầu)
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).replace(['None', 'nan', '<NA>'], '').str.strip()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Merge thông tin nhân sự vào Assets
        df_main = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # Xử lý các giá trị Null sau Merge
        fill_values = {
            'full_name': 'Hệ thống / Kho',
            'department': 'Chưa gán',
            'branch': 'Toàn quốc'
        }
        df_main = df_main.fillna(value=fill_values)

        # -------------------------------------------------
        # 3. ENTERPRISE SIDEBAR FILTERS (Global)
        # -------------------------------------------------
        with st.sidebar:
            st.header("🎯 Điều khiển Dashboard")
            
            # Filter Vùng miền
            branches = ["Tất cả"] + sorted(df_main['branch'].unique().tolist())
            sel_branch = st.selectbox("Chi nhánh", branches)
            
            # Filter Phòng ban
            depts = ["Tất cả"] + sorted(df_main['department'].unique().tolist())
            sel_dept = st.selectbox("Phòng ban", depts)
            
            # Filter Loại thiết bị
            types = ["Tất cả"] + sorted(df_main['type'].unique().tolist())
            sel_type = st.selectbox("Loại tài sản", types)

        # 4. GLOBAL SEARCH
        search_query = st.text_input("🔍 Tìm kiếm tài sản", placeholder="Nhập mã máy (PC0001) hoặc tên nhân viên...")

        # Áp dụng logic lọc đa tầng
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
        # 5. INTEGRATE AI ENGINE (The "Pro" Guard)
        # -------------------------------------------------
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)

        # Gọi AI Engine
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # ĐẢM BẢO CỘT 'full_name' QUAY TRỞ LẠI: 
        # Nếu AI Engine làm mất cột full_name, ta merge lại một lần nữa dựa trên asset_tag
        if 'full_name' not in df_ai.columns:
            df_ai = pd.merge(df_ai, df_main[['asset_tag', 'full_name']], on='asset_tag', how='left')

        # -------------------------------------------------
        # 6. HIỂN THỊ GIAO DIỆN (Visual Drill-down)
        # -------------------------------------------------
        # KPI Row
        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng thiết bị", len(df_filtered), help="Số lượng máy tính/thiết bị đang hiển thị theo bộ lọc")
        k2.metric("🚨 Rủi ro Nguy cấp", metrics.get("critical_assets", 0))
        k3.metric("🔑 Bản quyền lỗi", metrics.get("license_alerts", 0))
        k4.metric("⚙️ MTTR (Trung bình)", metrics.get("mttr", "N/A"))

        # Main Visualization
        st.markdown("---")
        col_pie, col_table = st.columns([5, 5])
        
        with col_pie:
            st.subheader("📊 Mức độ rủi ro (AI Predicted)")
            fig = px.pie(
                df_ai, names='risk_level', hole=0.6,
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#FF4B4B", 
                    "🟠 Cao": "#FFA500", 
                    "🟡 Trung bình": "#F0E68C",
                    "🟢 Thấp": "#28A745"
                }
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.subheader("📋 Danh sách Drill-down")
            st.caption("Chi tiết thiết bị tương ứng với bộ lọc hiện tại")
            # Hiển thị bảng chi tiết cực kỳ chuyên nghiệp
            st.dataframe(
                df_ai[['asset_tag', 'full_name', 'risk_level', 'status']].rename(columns={
                    'asset_tag': 'Mã máy',
                    'full_name': 'Người sử dụng',
                    'risk_level': 'Mức độ rủi ro',
                    'status': 'Trạng thái'
                }),
                use_container_width=True,
                hide_index=True,
                height=350
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
        st.exception(e) # Hiển thị chi tiết lỗi cho developer (bạn)

def render_usage_details(supabase):
    """Tab 5: Truy xuất chi tiết phần mềm & nhân sự"""
    render_dashboard(supabase)
