import streamlit as st
import pandas as pd
import plotly.express as px # Cần cài đặt: pip install plotly
from .ai_engine import calculate_ai_metrics # Giả định bạn để hàm AI trong ai_engine.py

def render_dashboard(supabase):
    st.header("📊 Hệ thống Phân tích & Dự báo Tài sản (AI)")
    
    # 1. TẢI DỮ LIỆU TỪ SUPABASE
    try:
        # Lấy dữ liệu Assets
        res_assets = supabase.table("assets").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)

        # CẬP NHẬT DÒNG NÀY: Đổi 'maintenance_history' thành 'maintenance_log'
        res_maint = supabase.table("maintenance_log").select("*").execute()
        df_maint = pd.DataFrame(res_maint.data)

        # Lấy dữ liệu Bản quyền (Licenses)
        res_lic = supabase.table("licenses").select("*").execute()
        df_lic = pd.DataFrame(res_lic.data)

    except Exception as e:
        st.error(f"❌ Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    # 2. XỬ LÝ AI METRICS (HỨNG ĐỦ 6 THAM SỐ)
    if not df_assets.empty:
        # Gọi hàm AI chiến lược
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = calculate_ai_metrics(df_assets, df_maint, df_lic)

        # 3. HIỂN THỊ METRICS TỔNG QUAN (KPI CARDS)
        st.markdown("---")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        
        with m_col1:
            st.metric("⏳ MTBF", metrics["mtbf"], help="Thời gian trung bình giữa các lần hỏng")
        with m_col2:
            st.metric("🛠️ MTTR", metrics["mttr"], help="Thời gian trung bình để sửa chữa")
        with m_col3:
            st.metric("🚨 Nguy cấp", metrics["critical_assets"], delta="Cần thay thế ngay", delta_color="inverse")
        with m_col4:
            st.metric("🟠 Rủi ro cao", metrics["high_risk_assets"])
        with m_col5:
            st.metric("🔑 License", metrics["license_alerts"], delta="Hết hạn/Thiếu")

        st.markdown("---")

        # 4. PHÂN TÍCH CHI TIẾT (LAYOUT 2 CỘT)
        col_left, col_right = st.columns([6, 4])

        with col_left:
            st.subheader("📍 Bản đồ Rủi ro theo Chi nhánh")
            # Vẽ biểu đồ cột chuyên nghiệp với Plotly
            fig_branch = px.bar(
                b_stats.reset_index(), 
                x='branch', 
                y='Rủi ro TB',
                color='Rủi ro TB',
                color_continuous_scale='Reds',
                labels={'branch': 'Chi nhánh', 'Rủi ro TB': 'Chỉ số rủi ro'},
                text_auto='.2f'
            )
            fig_branch.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_branch, use_container_width=True)

            st.subheader("🔍 Danh sách Tài sản Nguy cấp (Cần xử lý)")
            critical_list = df_ai[df_ai['risk_level'] == "🔴 Nguy cấp"][['asset_tag', 'type', 'assigned_to', 'failure_prob']]
            st.dataframe(critical_list.sort_values('failure_prob', ascending=False), use_container_width=True)

        with col_right:
            st.subheader("🏢 Phân bổ Rủi ro theo Nhóm")
            # Biểu đồ tròn phân bổ rủi ro
            fig_pie = px.pie(
                df_ai, 
                names='risk_level', 
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#ff4b4b",
                    "🟠 Cao": "#ffa500",
                    "🟡 Trung bình": "#ffd700",
                    "🟢 Thấp": "#28a745"
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("👤 Top 10 User cần lưu ý")
            # Hiển thị bảng Top User với màu sắc cảnh báo
            st.dataframe(
                u_stats.style.background_gradient(cmap='YlOrRd', subset=['Tổng lượt hỏng', 'Rủi ro Max']),
                use_container_width=True
            )

        # 5. PHÂN TÍCH BẢN QUYỀN (LICENSES)
        if not lic_ai.empty:
            st.markdown("---")
            st.subheader("🌐 Tình trạng Bản quyền & Phần mềm")
            # Lọc các license có rủi ro
            risk_licenses = lic_ai[lic_ai['license_risk'] != "✅ Ổn định"]
            if not risk_licenses.empty:
                st.warning(f"Phát hiện {len(risk_licenses)} phần mềm đang trong tình trạng nguy cấp hoặc sắp hết hạn.")
                st.table(risk_licenses[['software_name', 'remaining', 'usage_ratio', 'license_risk']])
            else:
                st.success("Tất cả bản quyền phần mềm đang ở trạng thái ổn định.")

    else:
        st.info("👋 Chào mừng! Hiện tại chưa có dữ liệu tài sản để phân tích. Hãy thêm tài sản mới tại tab 'Cấp phát & Kho'.")
