import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="pro_max_v2"):
    # --- CSS NÂNG CẤP: GIAO DIỆN SẠCH (APPLE DESIGN LANGUAGE) ---
    st.markdown("""
        <style>
        .main-card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #e5e5e7;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🍎 Enterprise Asset Intelligence")
    
    try:
        # 1. TRUY XUẤT DỮ LIỆU GỐC
        with st.spinner("Đang kết nối trung tâm dữ liệu..."):
            res_assets = supabase.table("assets").select("*").execute()
            res_staff = supabase.table("staff").select("*").execute()
            
            df_assets = pd.DataFrame(res_assets.data)
            df_staff = pd.DataFrame(res_staff.data)

        if df_assets.empty:
            st.warning("Kho dữ liệu đang trống.")
            return

        # 2. TIỀN XỬ LÝ ĐỒNG BỘ
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).str.replace(r'\.0$', '', regex=True)
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].replace(['nan', 'None', 'null', ''], np.nan)

        # 3. GỌI AI ENGINE (Nhận về df_ai đã được gộp nhóm)
        metrics, df_ai, _, b_stats, d_stats, _ = ai_engine.calculate_ai_metrics(
            df_assets, None, None, df_staff
        )

        # --- FIX LỖI: Kiểm tra chính xác tên cột có trong df_ai ---
        # Tùy vào ai_engine trả về 'Mã NV' hay 'Mã NV/Kho', ta sẽ dùng cột đó để nhận diện nhân sự
        col_id = 'Mã NV' if 'Mã NV' in df_ai.columns else ('Mã NV/Kho' if 'Mã NV/Kho' in df_ai.columns else df_ai.columns[0])

        # 4. KHỐI CHỈ SỐ KPI
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Tổng thiết bị", f"{df_ai['Số lượng'].sum()} 🖥️")
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            # Chỉ đếm những dòng không phải là Kho
            staff_count = len(df_ai[df_ai[col_id] != "---"])
            st.metric("Nhân sự sở hữu", f"{staff_count} 👤")
            st.markdown('</div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Bản quyền", f"{metrics.get('license_alerts', 0)} 🔑")
            st.markdown('</div>', unsafe_allow_html=True)
        with c4:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("Trạng thái", "Ổn định 🟢")
            st.markdown('</div>', unsafe_allow_html=True)

        # 5. BIỂU ĐỒ TRỰC QUAN (Visual Analytics)
        v_left, v_right = st.columns(2)
        with v_left:
            if not b_stats.empty:
                st.write("##### 📍 Phân bổ vùng miền")
                fig_br = px.pie(b_stats, values='asset_count', names='branch', hole=0.5,
                                color_discrete_sequence=px.colors.qualitative.Safe)
                fig_br.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250, showlegend=False)
                st.plotly_chart(fig_br, use_container_width=True)
        
        with v_right:
            if not d_stats.empty:
                st.write("##### 🏢 Mật độ phòng ban")
                fig_dept = px.bar(d_stats.sort_values('asset_count'), x='asset_count', y='department', 
                                  orientation='h', color_discrete_sequence=['#0071e3'])
                fig_dept.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250, xaxis_title=None, yaxis_title=None)
                st.plotly_chart(fig_dept, use_container_width=True)

        # 6. BẢNG DRILL-DOWN (Sửa lỗi Search & Index)
        st.markdown("---")
        search = st.text_input("🔍 Tìm kiếm thông minh", placeholder="Nhập tên nhân viên hoặc mã máy...")

        df_display = df_ai.copy()
        if search:
            # Tìm kiếm linh hoạt trên các cột hiện có
            mask = df_display['Mã máy'].str.contains(search, case=False, na=False) | \
                   df_display['Nhân viên sở hữu'].str.contains(search, case=False, na=False)
            df_display = df_display[mask]

        st.dataframe(
            df_display,
            column_config={
                col_id: st.column_config.TextColumn("ID"),
                "Nhân viên sở hữu": st.column_config.TextColumn("👤 Nhân sự", width="medium"),
                "Mã máy": st.column_config.TextColumn("🖥️ Danh sách thiết bị", width="large"),
                "Số lượng": st.column_config.NumberColumn("SL", format="%d")
            },
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.error(f"⚠️ Lỗi cấu trúc Dashboard: {str(e)}")
        st.info("Mẹo: Đảm bảo hàm calculate_ai_metrics trong ai_engine trả về đúng các cột 'Mã máy' và 'Nhân viên sở hữu'.")
