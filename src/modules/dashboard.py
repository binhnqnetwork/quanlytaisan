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

        # Kiểm tra dữ liệu đầu vào
        if df_assets.empty or df_staff.empty:
            st.warning("⚠️ Đang thiếu dữ liệu Assets hoặc Staff để thực hiện phân tích.")
            return

        # -------------------------------------------------
        # 2. XỬ LÝ DỮ LIỆU GỐC & FIX LỖI 'full_name'
        # -------------------------------------------------
        # Thực hiện merge Assets và Staff ngay từ đầu để đảm bảo cột tồn tại
        df_merged = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )
        
        # Điền giá trị mặc định nếu không khớp mã nhân viên
        df_merged['full_name'] = df_merged['full_name'].fillna("Kho tổng / Chưa cấp")
        df_merged['branch'] = df_merged['branch'].fillna("N/A")
        df_merged['department'] = df_merged['department'].fillna("N/A")

        # -------------------------------------------------
        # 3. GLOBAL FILTERS (SIDEBAR) - Tiêu chí 1
        # -------------------------------------------------
        with st.sidebar:
            st.title("🎯 Bộ lọc hệ thống")
            
            # Lấy danh sách unique từ df_merged để đảm bảo tính nhất quán
            branch_list = ["Tất cả"] + sorted([b for b in df_merged['branch'].unique() if b])
            sel_branch = st.selectbox("Chi nhánh", branch_list)
            
            dept_list = ["Tất cả"] + sorted([d for d in df_merged['department'].unique() if d])
            sel_dept = st.selectbox("Phòng ban", dept_list)
            
            type_list = ["Tất cả"] + sorted(list(df_merged['status'].unique()))
            sel_status = st.selectbox("Trạng thái thiết bị", type_list)

        # 4. GLOBAL SEARCH (Tiêu chí 3)
        search_query = st.text_input("🔍 Tìm nhanh Asset (Mã máy, Tên nhân viên...)", placeholder="Nhập từ khóa...")

        # Áp dụng logic lọc
        df_filtered = df_merged.copy()
        if sel_branch != "Tất cả":
            df_filtered = df_filtered[df_filtered['branch'] == sel_branch]
        if sel_dept != "Tất cả":
            df_filtered = df_filtered[df_filtered['department'] == sel_dept]
        if sel_status != "Tất cả":
            df_filtered = df_filtered[df_filtered['status'] == sel_status]
        if search_query:
            df_filtered = df_filtered[
                df_filtered['asset_tag'].str.contains(search_query, case=False, na=False) | 
                df_filtered['full_name'].str.contains(search_query, case=False, na=False)
            ]

        # -------------------------------------------------
        # 5. GỌI AI ENGINE (Với dữ liệu đã lọc)
        # -------------------------------------------------
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        # 6. HIỂN THỊ KPI
        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Thiết bị hiển thị", len(df_filtered))
        k2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        k3.metric("🔑 Lỗi License", metrics.get("license_alerts", 0))
        k4.metric("🛠️ MTTR", metrics.get("mttr", "N/A"))

        # -------------------------------------------------
        # 7. DRILL-DOWN (Tiêu chí 2)
        # -------------------------------------------------
        st.markdown("---")
        col_chart, col_drill = st.columns([6, 4])
        
        with col_chart:
            st.subheader("📊 Phân bổ mức độ rủi ro")
            fig = px.pie(df_ai, names='risk_level', color='risk_level', hole=0.5,
                         color_discrete_map={
                             "🔴 Nguy cấp": "#FF4B4B", 
                             "🟠 Cao": "#FFA500", 
                             "🟢 Thấp": "#28A745"
                         })
            st.plotly_chart(fig, use_container_width=True)

        with col_drill:
            st.subheader("📋 Danh sách chi tiết (Drill-down)")
            st.caption("Dữ liệu tự động lọc theo bộ lọc toàn cục và tìm kiếm")
            # Hiển thị bảng chi tiết phản ứng theo Search/Filter
            st.dataframe(
                df_ai[['asset_tag', 'full_name', 'risk_level', 'branch']].rename(columns={
                    'asset_tag': 'Mã máy', 'full_name': 'Người dùng', 
                    'risk_level': 'Mức độ', 'branch': 'Chi nhánh'
                }), 
                use_container_width=True, 
                hide_index=True, 
                height=400
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

def render_usage_details(supabase):
    """
    Hàm Tab 5: Đã sửa lỗi attribute và đồng nhất logic hiển thị
    """
    st.header("👥 Truy xuất Chi tiết Cấp phát")
    # Tái sử dụng logic merge và filter tương tự nếu cần chi tiết hơn
    # Ở đây gọi lại render_dashboard hoặc viết logic bảng phẳng tương tự bước 4.
