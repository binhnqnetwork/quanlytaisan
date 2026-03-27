import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from . import ai_engine

def render_dashboard(supabase, key_prefix="pro_max"):
    # --- CSS NÂNG CẤP: GLASSMORPHISM STYLE ---
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] { font-size: 28px !important; color: #1d1d1f; }
        .main-card {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            border: 1px solid rgba(209, 209, 214, 0.5);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🚀 Enterprise Asset Intelligence")
    
    try:
        # 1. DATA ACQUISITION
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)

        # Tiền xử lý nhanh
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).str.replace(r'\.0$', '', regex=True)
        
        # 2. AI ENGINE PROCESSING
        metrics, df_ai, _, b_stats, d_stats, _ = ai_engine.calculate_ai_metrics(
            df_assets, None, None, df_staff
        )

        # 3. TOP KPI SECTION (APPLE STYLE CARDS)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Tổng thiết bị", f"{df_ai['Số lượng'].sum()} 🖥️")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Nhân sự nắm giữ", f"{len(df_ai[df_ai['Mã NV'] != '---'])} 👤")
            st.markdown('</div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Bản quyền", f"{metrics.get('license_alerts', 0)} 🔑", delta="-2% week")
            st.markdown('</div>', unsafe_allow_html=True)
        with col4:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Rủi ro vận hành", "Thấp 🟢")
            st.markdown('</div>', unsafe_allow_html=True)

        # 4. TRỰC QUAN HÓA DỮ LIỆU (THE POWER OF VISUALS)
        c_left, c_right = st.columns([1, 1])

        with c_left:
            st.markdown("##### 📍 Phân bổ theo Chi nhánh")
            # Dùng Pie Chart phong cách hiện đại
            fig_br = px.pie(b_stats, values='asset_count', names='branch', 
                            hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_br.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, showlegend=True)
            st.plotly_chart(fig_br, use_container_width=True)

        with c_right:
            st.markdown("##### 🏢 Tài sản theo Phòng ban")
            # Dùng Bar Chart nằm ngang (Donut style bars)
            fig_dept = px.bar(d_stats.sort_values('asset_count'), x='asset_count', y='department', 
                              orientation='h', color='asset_count', color_continuous_scale='Blues')
            fig_dept.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300, coloraxis_showscale=False)
            st.plotly_chart(fig_dept, use_container_width=True)

        # 5. DRILL-DOWN TABLE (PEOPLE-CENTRIC)
        st.markdown("---")
        st.markdown("##### 🔍 Chi tiết cấp phát & Truy xuất nhanh")
        
        # Thanh tìm kiếm tích hợp gọn gàng
        search = st.text_input("Tìm kiếm thông minh...", placeholder="Gõ tên nhân viên hoặc mã máy để lọc ngay...")
        
        df_final = df_ai.copy()
        if search:
            df_final = df_final[
                df_final['Mã máy'].str.contains(search, case=False, na=False) |
                df_final['Nhân viên sở hữu'].str.contains(search, case=False, na=False)
            ]

        st.dataframe(
            df_final,
            column_config={
                "Mã máy": st.column_config.TextColumn("🔖 Định danh tài sản"),
                "Nhân viên sở hữu": st.column_config.TextColumn("👤 Người dùng"),
                "Số lượng": st.column_config.ProgressColumn("SL", format="%d", min_value=0, max_value=5)
            },
            use_container_width=True, hide_index=True
        )

    except Exception as e:
        st.error(f"Hệ thống đang bảo trì Dashboard: {e}")
