import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine  # Đảm bảo file ai_engine.py nằm cùng thư mục modules

def render_dashboard(supabase):
    """
    TAB 4: Dashboard Phân tích AI & Thống kê Tổng thể
    Khôi phục đầy đủ chức năng gọi tới ai_engine.py
    """
    st.header("📊 Hệ thống Phân tích & Dự báo Tài sản (AI)")
    
    try:
        # 1. Tải toàn bộ dữ liệu cần thiết cho AI Engine
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("employee_code, full_name, department, branch").execute()
        res_maint = supabase.table("maintenance_log").select("*").execute()
        res_lic = supabase.table("licenses").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        df_maint = pd.DataFrame(res_maint.data)
        df_lic = pd.DataFrame(res_lic.data)

        if not df_assets.empty:
            # 2. GỌI AI ENGINE (Khôi phục chức năng thống kê)
            metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
                df_assets, df_maint, df_lic, df_staff
            )

            # 3. Hiển thị KPI Cards từ AI Metrics
            st.markdown("---")
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1: st.metric("⏳ MTBF (Dự kiến)", metrics.get("mtbf", "N/A"))
            with m_col2: st.metric("🛠️ MTTR (Trung bình)", metrics.get("mttr", "N/A"))
            with m_col3: st.metric("🚨 Máy Nguy cấp", metrics.get("critical_assets", 0), delta_color="inverse")
            with m_col4: st.metric("🟠 Rủi ro cao", metrics.get("high_risk_assets", 0))
            with m_col5: st.metric("🔑 Cảnh báo License", metrics.get("license_alerts", 0))

            # 4. Biểu đồ Phân tích Rủi ro
            st.markdown("---")
            col_left, col_right = st.columns([6, 4])
            
            with col_left:
                st.subheader("📍 Chỉ số Rủi ro theo Chi nhánh")
                fig_bar = px.bar(b_stats, x='branch', y='Rủi ro TB', 
                                 color='Rủi ro TB', color_continuous_scale='Reds',
                                 labels={'branch': 'Chi nhánh', 'Rủi ro TB': 'Mức độ rủi ro'})
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_right:
                st.subheader("🏢 Tỷ lệ Mức độ Rủi ro")
                fig_pie = px.pie(df_ai, names='risk_level', color='risk_level',
                                 color_discrete_map={
                                     "🔴 Nguy cấp": "#ff4b4b", 
                                     "🟠 Cao": "#ffa500", 
                                     "🟡 Trung bình": "#ffd700", 
                                     "🟢 Thấp": "#28a745"
                                 })
                st.plotly_chart(fig_pie, use_container_width=True)

            # 5. Bảng Cảnh báo License (Nếu có)
            if not lic_ai.empty:
                st.markdown("---")
                st.subheader("🌐 Tình trạng Bản quyền (AI Alert)")
                risk_lic = lic_ai[lic_ai['license_risk'] != "✅ Ổn định"]
                if not risk_lic.empty:
                    st.dataframe(risk_lic[['software_name', 'expiry_date', 'remaining', 'license_risk']].rename(columns={
                        'software_name': 'Phần mềm', 'expiry_date': 'Hết hạn', 
                        'remaining': 'Còn lại', 'license_risk': 'Trạng thái'
                    }), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ Tất cả License đều trong ngưỡng an toàn.")

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard AI: {e}")

def render_usage_details(supabase):
    """
    TAB 5: Truy xuất Chi tiết Cấp phát (Đã sửa lỗi Attribute)
    """
    st.header("👥 Truy xuất Chi tiết Cấp phát License & Nhân sự")
    
    try:
        # 1. Tải dữ liệu
        df_assets = pd.DataFrame(supabase.table("assets").select("*").execute().data)
        df_staff = pd.DataFrame(supabase.table("staff").select("employee_code, full_name, department, branch").execute().data)

        if not df_assets.empty and not df_staff.empty:
            # 2. Join dữ liệu để lấy tên và phòng ban
            df_final = pd.merge(df_assets, df_staff, left_on='assigned_to_code', right_on='employee_code', how='left')
            
            # Xử lý hiển thị
            df_final['software_display'] = df_final['software_list'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "Trống")
            df_final['full_name'] = df_final['full_name'].fillna("Trong kho/Chưa cấp")

            # 3. Bộ lọc tìm kiếm
            col_search, col_branch = st.columns([2, 1])
            with col_search:
                query = st.text_input("🔍 Tìm theo tên, mã NV hoặc phần mềm...")
            with col_branch:
                branches = [b for b in df_final['branch'].unique() if b]
                branch_sel = st.multiselect("Vùng miền", branches, default=branches)

            # 4. Filter dữ liệu
            mask = df_final['branch'].isin(branch_sel)
            if query:
                mask = mask & (
                    df_final['full_name'].str.contains(query, case=False, na=False) |
                    df_final['software_display'].str.contains(query, case=False) |
                    df_final['assigned_to_code'].astype(str).str.contains(query)
                )

            # 5. Hiển thị bảng chi tiết (BỎ CỘT SPECS)
            st.dataframe(
                df_final[mask][[
                    'asset_tag', 'assigned_to_code', 'full_name', 'department', 'branch', 'software_display', 'status'
                ]].rename(columns={
                    'asset_tag': 'Mã Máy', 'assigned_to_code': 'Mã NV', 'full_name': 'Tên Nhân Viên',
                    'department': 'Phòng Ban', 'branch': 'Vùng miền', 'software_display': 'License đang dùng', 'status': 'Trạng thái'
                }), use_container_width=True, hide_index=True
            )
    except Exception as e:
        st.error(f"❌ Lỗi Chi tiết sử dụng: {e}")
