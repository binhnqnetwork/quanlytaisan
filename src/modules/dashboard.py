import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine  # Đảm bảo import đúng alias

def render_dashboard(supabase):
    st.header("📊 Hệ thống Phân tích & Dự báo Tài sản (AI)")
    
    # 1. TẢI DỮ LIỆU TỔNG HỢP TỪ SUPABASE
    try:
        # Tải Assets
        res_assets = supabase.table("assets").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)

        # Tải Staff để mapping thông tin người dùng vào AI Engine
        res_staff = supabase.table("staff").select("employee_code, full_name, department, branch").execute()
        df_staff = pd.DataFrame(res_staff.data)

        # Tải Maintenance (nếu có)
        res_maint = supabase.table("maintenance_log").select("*").execute()
        df_maint = pd.DataFrame(res_maint.data)

        # Tải Licenses
        res_lic = supabase.table("licenses").select("*").execute()
        df_lic = pd.DataFrame(res_lic.data)

    except Exception as e:
        st.error(f"❌ Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    # 2. XỬ LÝ AI METRICS (Truyền thêm df_staff để mapping)
    if not df_assets.empty:
        # Gọi hàm từ ai_engine đã hoàn thiện của bạn
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_assets, df_maint, df_lic, df_staff
        )

        # 3. KPI CARDS - Chỉ số thông minh
        st.markdown("---")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1: st.metric("⏳ MTBF (Độ bền)", metrics["mtbf"])
        with m_col2: st.metric("🛠️ MTTR (Sửa chữa)", metrics["mttr"])
        with m_col3: st.metric("🚨 Nguy cấp", metrics["critical_assets"], delta_color="inverse")
        with m_col4: st.metric("🟠 Rủi ro cao", metrics["high_risk_assets"])
        with m_col5: st.metric("🔑 License Alert", metrics["license_alerts"])

        st.markdown("---")

        # 4. PHÂN TÍCH CHI TIẾT THEO CHI NHÁNH & RỦI RO
        col_left, col_right = st.columns([6, 4])

        with col_left:
            st.subheader("📍 Bản đồ Rủi ro theo Chi nhánh")
            fig_branch = px.bar(
                b_stats, 
                x='branch', y='Rủi ro TB', color='Rủi ro TB',
                color_continuous_scale='Reds',
                labels={'branch': 'Chi nhánh', 'Rủi ro TB': 'Chỉ số rủi ro'},
                text_auto='.2f'
            )
            fig_branch.update_layout(height=400)
            st.plotly_chart(fig_branch, use_container_width=True)

            st.subheader("🔍 Danh sách Tài sản Nguy cấp (🔴)")
            # Hiển thị thông tin người dùng thay vì chỉ mã code
            critical_display = df_ai[df_ai['risk_level'] == "🔴 Nguy cấp"][[
                'asset_tag', 'full_name', 'department', 'risk_score'
            ]].sort_values('risk_score', ascending=False)
            
            st.dataframe(
                critical_display.rename(columns={
                    'asset_tag': 'Mã Máy', 'full_name': 'Người giữ',
                    'department': 'Phòng ban', 'risk_score': 'Điểm rủi ro'
                }), 
                use_container_width=True, hide_index=True
            )

        with col_right:
            st.subheader("🏢 Tỷ lệ Mức độ Rủi ro")
            fig_pie = px.pie(
                df_ai, names='risk_level', 
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#ff4b4b", "🟠 Cao": "#ffa500",
                    "🟡 Trung bình": "#ffd700", "🟢 Thấp": "#28a745"
                },
                hole=0.4
            )
            fig_pie.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("👤 Top 10 User rủi ro nhất")
            # Hiển thị bảng Top 10 với màu sắc cảnh báo
            st.dataframe(
                u_stats.style.background_gradient(cmap='YlOrRd', subset=['Rủi ro Max']),
                use_container_width=True,
                hide_index=True
            )

        # 5. PHÂN TÍCH LICENSE (Đã đồng bộ hóa tên cột)
        if not lic_ai.empty:
            st.markdown("---")
            st.subheader("🌐 Quản lý Bản quyền phần mềm")
            
            risk_licenses = lic_ai[lic_ai['license_risk'] != "✅ Ổn định"]
            
            if not risk_licenses.empty:
                st.warning(f"Phát hiện {len(risk_licenses)} phần mềm cần xử lý ngay.")
                st.dataframe(
                    risk_licenses[['software_name', 'used_quantity', 'total_quantity', 'remaining', 'license_risk']]
                    .rename(columns={
                        'software_name': 'Phần mềm', 'used_quantity': 'Đã dùng',
                        'total_quantity': 'Tổng cấp', 'remaining': 'Còn lại', 'license_risk': 'Trạng thái'
                    }),
                    use_container_width=True, hide_index=True
                )
            else:
                st.success("Tất cả License đang trong ngưỡng an toàn.")

    else:
        st.info("👋 Chưa có dữ liệu tài sản để hệ thống AI phân tích.")
