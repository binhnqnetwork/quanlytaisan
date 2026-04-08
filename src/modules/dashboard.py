import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="master_fix_v4"):
    st.markdown("""
        <style>
        .main-card {
            background: white; border-radius: 16px; padding: 20px;
            border: 1px solid #e5e5e7; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
            min-height: 120px;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        # 1. TRUY XUẤT & TIỀN XỬ LÝ
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)

        for df, col in [(df_assets, 'assigned_to_code'), (df_staff, 'employee_code')]:
            df[col] = df[col].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df[col] = df[col].replace(['nan', 'None', 'null', '<NA>', ''], np.nan)

        # 2. GỌI AI ENGINE
        metrics, df_ai, _, _, _, _ = ai_engine.calculate_ai_metrics(
            df_assets, None, None, df_staff
        )

        # ĐỒNG BỘ TÊN CỘT
        rename_map = {
            'branch': 'Chi nhánh',
            'department': 'Phòng ban',
            'full_name': 'Nhân viên sở hữu',
            'asset_tag': 'Mã máy',
            'category': 'Loại'
        }
        df_ai = df_ai.rename(columns=rename_map)

        # 3. LOGIC LỌC (Sử dụng session_state từ app.py)
        df_display = df_ai.copy()
        
        # Lọc theo Chi nhánh từ Sidebar của app.py
        if "f_branch" in st.session_state and st.session_state.f_branch != "Tất cả chi nhánh":
            df_display = df_display[df_display['Chi nhánh'] == st.session_state.f_branch]
        
        # Lọc theo Tìm kiếm nhanh từ Sidebar của app.py
        if "f_search" in st.session_state and st.session_state.f_search:
            search_q = st.session_state.f_search
            df_display = df_display[
                df_display['Mã máy'].astype(str).str.contains(search_q, case=False, na=False) |
                df_display['Nhân viên sở hữu'].astype(str).str.contains(search_q, case=False, na=False)
            ]

        # 4. HIỂN THỊ KPI (ĐÃ SỬA CHUẨN)
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            total_m = len(df_display)
            st.metric("Tổng thiết bị", f"{total_m} máy")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with m2:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            # Nguy cấp: Lọc theo risk_level trong dữ liệu hiện tại
            crit_val = len(df_display[df_display['risk_level'].isin(['Cao', 'Rất cao', 'Critical'])]) if 'risk_level' in df_display.columns else 0
            st.metric("🚨 Nguy cấp", crit_val)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with m3:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            # --- FIX BẢN QUYỀN: Đếm trực tiếp từ cột Loại/category ---
            target_col = 'Loại' if 'Loại' in df_display.columns else 'category'
            if target_col in df_display.columns:
                lic_val = len(df_display[df_display[target_col].str.contains('License|Bản quyền|Software|Key', case=False, na=False)])
            else:
                lic_val = metrics.get("license_alerts", 0)
            st.metric("🔑 Bản quyền", f"{lic_val} Key")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with m4:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            st.metric("⚙️ MTTR", f"{metrics.get('mttr', 0)}h")
            st.markdown('</div>', unsafe_allow_html=True)

        # 5. BIỂU ĐỒ & BẢNG
        c_l, c_r = st.columns([1, 1])
        with c_l:
            if 'Chi nhánh' in df_display.columns and not df_display.empty:
                fig = px.pie(df_display, names='Chi nhánh', hole=0.5, height=250, title="Tỷ lệ vùng miền")
                fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Không có dữ liệu biểu đồ")
        
        with c_r:
            # Có thể thêm biểu đồ cột hoặc thông tin phụ ở đây
            st.write("")

        st.markdown("---")
        st.markdown("### 📋 Danh sách chi tiết")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

# LƯU Ý: KHÔNG GỌI HÀM render_dashboard(supabase) Ở ĐÂY ĐỂ TRÁNH LỖI ĐỆ QUY
