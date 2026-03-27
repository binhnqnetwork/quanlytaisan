import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="master_pro"):
    # --- 1. APPLE DESIGN SYSTEM (CSS) ---
    st.markdown("""
        <style>
        .main-card {
            background: white; border-radius: 16px; padding: 20px;
            border: 1px solid #e5e5e7; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 600; color: #1d1d1f; }
        .stDataFrame { border-radius: 12px; overflow: hidden; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🏢 Hệ Thống Quản Trị Tài Sản Doanh Nghiệp")

    try:
        # --- 2. TRUY XUẤT DỮ LIỆU (Giữ nguyên luồng của pro) ---
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

        # --- 3. TIỀN XỬ LÝ ĐẮT TIỀN (Giữ nguyên logic ép kiểu của pro) ---
        for df, col in [(df_assets, 'assigned_to_code'), (df_staff, 'employee_code')]:
            df[col] = df[col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df[col] = df[col].replace(['nan', 'None', 'null', '<NA>', ''], np.nan)

        # --- 4. GỌI AI ENGINE (Xử lý gộp dòng People-centric) ---
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_assets, df_maint, df_lic, df_staff
        )
        
        # Tự động nhận diện cột ID (Mã NV hoặc Mã NV/Kho)
        col_id = 'Mã NV' if 'Mã NV' in df_ai.columns else ('Mã NV/Kho' if 'Mã NV/Kho' in df_ai.columns else 'ID')

        # --- 5. BỘ LỌC SIDEBAR ĐẮT TIỀN (Khôi phục logic của pro) ---
        with st.sidebar:
            st.header("🎯 Bộ lọc dữ liệu")
            # Lọc theo Branch (Chi nhánh)
            branches = ["Tất cả"] + sorted(df_ai['Chi nhánh'].dropna().unique().tolist())
            sel_branch = st.selectbox("Chi nhánh", branches, key=f"{key_prefix}_br")

            # Lọc theo Department (Phòng ban)
            depts = ["Tất cả"] + sorted(df_ai['Phòng ban'].dropna().unique().tolist())
            sel_dept = st.selectbox("Phòng ban", depts, key=f"{key_prefix}_de")

        # --- 6. LOGIC LỌC DỮ LIỆU HIỂN THỊ ---
        df_display = df_ai.copy()
        if sel_branch != "Tất cả":
            df_display = df_display[df_display['Chi nhánh'] == sel_branch]
        if sel_dept != "Tất cả":
            df_display = df_display[df_display['Phòng ban'] == sel_dept]

        # Tra cứu nhanh (Sửa lỗi search trên cột đã gộp)
        search = st.text_input("🔍 Tra cứu nhanh", placeholder="Nhập Mã máy hoặc Tên nhân sự...", key=f"{key_prefix}_se")
        if search:
            df_display = df_display[
                df_display['Mã máy'].str.contains(search, case=False, na=False) |
                df_display['Nhân viên sở hữu'].str.contains(search, case=False, na=False)
            ]

        # --- 7. KPI DASHBOARD (Visual Design nâng cấp) ---
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            total_m = df_display['Số lượng'].sum() if 'Số lượng' in df_display.columns else len(df_display)
            st.metric("Tổng thiết bị", f"{total_m} máy")
            st.markdown('</div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
            st.markdown('</div>', unsafe_allow_html=True)
        with m3:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("🔑 Bản quyền", metrics.get("license_alerts", 0))
            st.markdown('</div>', unsafe_allow_html=True)
        with m4:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("⚙️ MTTR", f"{metrics.get('mttr', 0)}h")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- 8. VISUAL ANALYTICS (Phần nâng cấp đồ họa) ---
        c_left, c_right = st.columns(2)
        with c_left:
            st.write("##### 📍 Phân bổ vùng miền")
            fig_br = px.pie(df_display.groupby('Chi nhánh').size().reset_index(name='count'), 
                            values='count', names='Chi nhánh', hole=0.5,
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_br.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=220, showlegend=False)
            st.plotly_chart(fig_br, use_container_width=True)
        
        with c_right:
            st.write("##### 🏢 Mật độ phòng ban")
            dept_count = df_display.groupby('Phòng ban').size().reset_index(name='count').sort_values('count')
            fig_dept = px.bar(dept_count, x='count', y='Phòng ban', orientation='h',
                              color_discrete_sequence=['#0071e3'])
            fig_dept.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=220, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_dept, use_container_width=True)

        # --- 9. DRILL-DOWN TABLE (Hoàn thiện cuối cùng) ---
        st.markdown("---")
        st.markdown("### 📋 Danh sách Drill-down Chi tiết")
        
        st.dataframe(
            df_display,
            column_config={
                col_id: st.column_config.TextColumn("ID"),
                "Nhân viên sở hữu": st.column_config.TextColumn("👤 Nhân sự", width="medium"),
                "Mã máy": st.column_config.TextColumn("🖥️ Danh sách thiết bị", width="large"),
                "Số lượng": st.column_config.NumberColumn("SL", format="%d"),
                "Mức độ rủi ro": st.column_config.TextColumn("⚠️ Rủi ro")
            },
            use_container_width=True, hide_index=True, height=500
        )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
