import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase, key_prefix="master_fix_v3"):
    st.markdown("""
        <style>
        .main-card {
            background: white; border-radius: 16px; padding: 20px;
            border: 1px solid #e5e5e7; box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        # 1. TRUY XUẤT & TIỀN XỬ LÝ (Giữ nguyên logic đắt tiền của pro)
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

        # --- BƯỚC QUAN TRỌNG: ĐỒNG BỘ TÊN CỘT (FIX LỖI 'Chi nhánh') ---
        # Kiểm tra nếu AI Engine trả về tiếng Anh thì đổi sang tiếng Việt để khớp với Filter
        rename_map = {
            'branch': 'Chi nhánh',
            'department': 'Phòng ban',
            'full_name': 'Nhân viên sở hữu',
            'asset_tag': 'Mã máy'
        }
        df_ai = df_ai.rename(columns=rename_map)

        # Xác định cột ID nhân viên
        col_id = 'Mã NV' if 'Mã NV' in df_ai.columns else ('Mã NV/Kho' if 'Mã NV/Kho' in df_ai.columns else df_ai.columns[0])

        # 3. SIDEBAR FILTER (Sử dụng tên cột đã đồng bộ)
        with st.sidebar:
            st.header("🎯 Bộ lọc dữ liệu")
            
            # Lấy danh sách Unique và xử lý lỗi nếu cột không tồn tại
            branch_list = sorted(df_ai['Chi nhánh'].dropna().unique().tolist()) if 'Chi nhánh' in df_ai.columns else []
            sel_branch = st.selectbox("Chi nhánh", ["Tất cả"] + branch_list, key=f"{key_prefix}_br")

            dept_list = sorted(df_ai['Phòng ban'].dropna().unique().tolist()) if 'Phòng ban' in df_ai.columns else []
            sel_dept = st.selectbox("Phòng ban", ["Tất cả"] + dept_list, key=f"{key_prefix}_de")

        # 4. LOGIC LỌC
        df_display = df_ai.copy()
        if sel_branch != "Tất cả":
            df_display = df_display[df_display['Chi nhánh'] == sel_branch]
        if sel_dept != "Tất cả":
            df_display = df_display[df_display['Phòng ban'] == sel_dept]

        # 5. TRA CỨU NHANH
        search = st.text_input("🔍 Tra cứu nhanh", placeholder="Nhập tên hoặc mã máy...", key=f"{key_prefix}_se")
        if search:
            df_display = df_display[
                df_display['Mã máy'].astype(str).str.contains(search, case=False, na=False) |
                df_display['Nhân viên sở hữu'].astype(str).str.contains(search, case=False, na=False)
            ]

        # 6. HIỂN THỊ KPI
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown('<div class="main-card">', unsafe_allow_html=True)
            total_m = df_display['Số lượng'].sum() if 'Số lượng' in df_display.columns else len(df_display)
            st.metric("Tổng thiết bị", f"{total_m} máy")
            st.markdown('</div>', unsafe_allow_html=True)
        # (Các cột m2, m3, m4 giữ nguyên như bản trước...)
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

        # 7. BIỂU ĐỒ & BẢNG
        c_l, c_r = st.columns(2)
        with c_l:
            if 'Chi nhánh' in df_display.columns:
                fig = px.pie(df_display, names='Chi nhánh', hole=0.5, height=220, title="Tỷ lệ vùng miền")
                fig.update_layout(margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")
        st.info("Kiểm tra lại tên cột trong file ai_engine.py")
