import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine  # Đảm bảo đường dẫn import ai_engine chính xác

def render_dashboard(supabase):
    """Hàm hiển thị giao diện Dashboard phân tích AI (Tab 4)"""
    st.header("📊 Hệ thống Phân tích & Dự báo Tài sản (AI)")
    
    try:
        # 1. Tải dữ liệu
        df_assets = pd.DataFrame(supabase.table("assets").select("*").execute().data)
        df_staff = pd.DataFrame(supabase.table("staff").select("employee_code, full_name, department, branch").execute().data)
        df_maint = pd.DataFrame(supabase.table("maintenance_log").select("*").execute().data)
        df_lic = pd.DataFrame(supabase.table("licenses").select("*").execute().data)

        if not df_assets.empty:
            # 2. Gọi AI Engine để xử lý dữ liệu
            metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
                df_assets, df_maint, df_lic, df_staff
            )

            # 3. Hiển thị KPI Cards
            st.markdown("---")
            m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
            with m_col1: st.metric("⏳ MTBF", metrics["mtbf"])
            with m_col2: st.metric("🛠️ MTTR", metrics["mttr"])
            with m_col3: st.metric("🚨 Nguy cấp", metrics["critical_assets"], delta_color="inverse")
            with m_col4: st.metric("🟠 Rủi ro cao", metrics["high_risk_assets"])
            with m_col5: st.metric("🔑 License", metrics["license_alerts"])

            # 4. Biểu đồ rủi ro
            st.markdown("---")
            col_l, col_r = st.columns([6, 4])
            with col_l:
                st.subheader("📍 Rủi ro theo Chi nhánh")
                fig_b = px.bar(b_stats, x='branch', y='Rủi ro TB', color='Rủi ro TB', color_continuous_scale='Reds')
                st.plotly_chart(fig_b, use_container_width=True)
            with col_r:
                st.subheader("🏢 Phân bổ Mức độ")
                fig_p = px.pie(df_ai, names='risk_level', color='risk_level', 
                               color_discrete_map={"🔴 Nguy cấp": "#ff4b4b", "🟠 Cao": "#ffa500", "🟡 Trung bình": "#ffd700", "🟢 Thấp": "#28a745"})
                st.plotly_chart(fig_p, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {e}")

def render_usage_details(supabase):
    """Hàm hiển thị bảng Chi tiết sử dụng (Tab 5) - FIX LỖI ATTRIBUTE ERROR"""
    st.header("👥 Truy xuất Chi tiết Cấp phát License & Nhân sự")
    
    try:
        # 1. Tải dữ liệu Assets và Staff
        res_assets = supabase.table("assets").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)

        res_staff = supabase.table("staff").select("employee_code, full_name, department, branch").execute()
        df_staff = pd.DataFrame(res_staff.data)

        if not df_assets.empty and not df_staff.empty:
            # 2. Join dữ liệu để lấy tên nhân viên thay vì mã code
            df_final = pd.merge(df_assets, df_staff, left_on='assigned_to_code', right_on='employee_code', how='left')
            
            # 3. Xử lý hiển thị danh sách phần mềm
            df_final['software_display'] = df_final['software_list'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) and len(x) > 0 else "Trống"
            )
            df_final['full_name'] = df_final['full_name'].fillna("Chưa cấp phát / Trong kho")

            # 4. Giao diện bộ lọc
            s_col, b_col = st.columns([2, 1])
            with s_col:
                search = st.text_input("🔍 Tìm theo Mã NV, Tên hoặc Phần mềm...", placeholder="Ví dụ: Photoshop, Hạnh, IT...")
            with b_col:
                branches = [b for b in df_final['branch'].unique() if b]
                branch_sel = st.multiselect("Vùng miền", options=branches, default=branches)

            # 5. Logic tìm kiếm
            mask = df_final['branch'].isin(branch_sel)
            if search:
                mask = mask & (
                    df_final['full_name'].str.contains(search, case=False, na=False) |
                    df_final['software_display'].str.contains(search, case=False) |
                    df_final['assigned_to_code'].astype(str).str.contains(search)
                )

            # 6. Hiển thị bảng (Bỏ cột specs rườm rà)
            st.dataframe(
                df_final[mask][[
                    'asset_tag', 'assigned_to_code', 'full_name', 'department', 'branch', 'software_display', 'status'
                ]].rename(columns={
                    'asset_tag': 'Mã Máy',
                    'assigned_to_code': 'Mã NV',
                    'full_name': 'Tên Nhân Viên',
                    'department': 'Phòng Ban',
                    'branch': 'Vùng miền',
                    'software_display': 'Bản quyền đang dùng',
                    'status': 'Trạng thái'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("⚠️ Không tìm thấy dữ liệu Assets hoặc Staff.")

    except Exception as e:
        st.error(f"❌ Lỗi Chi tiết sử dụng: {e}")
