import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from .ai_engine import calculate_ai_metrics

def render_dashboard(supabase):
    # --- 1. SETTINGS & ENTERPRISE UI ---
    st.markdown("""
        <style>
        .stMetric { background: white; padding: 20px; border-radius: 15px; border: 1px solid #efeff4; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
        [data-testid="stMetricValue"] { font-weight: 700; color: #0071e3; }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] { 
            height: 45px; background-color: #f5f5f7; border-radius: 10px; padding: 0px 20px; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #0071e3 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. DATA INGESTION & SMART PRE-PROCESSING ---
    try:
        # Fetch data
        assets_res = supabase.table("assets").select("*").execute()
        lic_res = supabase.table("licenses").select("*").execute()
        maint_res = supabase.table("maintenance_log").select("*").execute()
        staff_res = supabase.table("staff").select("employee_code", "full_name", "branch", "department").execute()

        df_assets = pd.DataFrame(assets_res.data) if assets_res.data else pd.DataFrame()
        df_lic = pd.DataFrame(lic_res.data) if lic_res.data else pd.DataFrame()
        df_maint = pd.DataFrame(maint_res.data) if maint_res.data else pd.DataFrame()
        df_staff = pd.DataFrame(staff_res.data) if staff_res.data else pd.DataFrame()
        
        # Định nghĩa nhãn thiết bị dùng chung
        type_labels = {'LT': 'Laptop', 'PC': 'Desktop PC', 'MN': 'Monitor', 'SV': 'Server', 'OT': 'Khác'}
        
        # Bổ sung Type Label ngay từ đầu cho df_assets
        if not df_assets.empty:
            df_assets['Type Label'] = df_assets['type'].map(type_labels).fillna('Khác')

        # AI Engine Processing (trả về df_ai đã tính toán rủi ro)
        ai_metrics, df_ai = calculate_ai_metrics(df_assets, df_maint, df_lic)
        
        # QUAN TRỌNG: Gán Type Label vào df_ai để tránh lỗi index khi vẽ scatter/dataframe
        if not df_ai.empty:
            df_ai['Type Label'] = df_ai['type'].map(type_labels).fillna('Khác')

        # Merge dữ liệu Master để lọc theo Chi nhánh/Bộ phận
        df_master = pd.merge(
            df_assets, 
            df_staff, 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        ).fillna({"branch": "Chưa phân bổ", "department": "Kho", "full_name": "N/A"})

    except Exception as e:
        st.error(f"Lỗi hệ thống dữ liệu: {e}")
        return

    # --- 3. SIDEBAR GLOBAL FILTERS ---
    st.sidebar.markdown("## 🔍 Bộ lọc Hệ thống")
    all_branches = sorted(df_master['branch'].unique().tolist())
    selected_branches = st.sidebar.multiselect("📍 Chọn Chi nhánh", options=all_branches, default=all_branches)
    
    relevant_depts = sorted(df_master[df_master['branch'].isin(selected_branches)]['department'].unique().tolist())
    selected_depts = st.sidebar.multiselect("🏢 Chọn Bộ phận", options=relevant_depts, default=relevant_depts)

    # Filter Master data
    df_filtered = df_master[
        (df_master['branch'].isin(selected_branches)) & 
        (df_master['department'].isin(selected_depts))
    ]

    # --- 4. HEADER & KPIs ---
    st.markdown('<h1 style="color: #1d1d1f; font-weight: 800;">🧠 AI Strategic Hub</h1>', unsafe_allow_html=True)
    st.caption(f"Dữ liệu đồng bộ Real-time: {datetime.now().strftime('%H:%M:%S')}")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Độ tin cậy (MTBF)", ai_metrics.get('mtbf', 'N/A'))
    k2.metric("Thời gian sửa (MTTR)", ai_metrics.get('mttr', 'N/A'))
    
    active_rate = (len(df_filtered[df_filtered['status']=='Đang sử dụng']) / len(df_filtered) * 100) if not df_filtered.empty else 0
    k3.metric("Hiệu suất sử dụng", f"{active_rate:.1f}%", f"{len(df_filtered)} máy")
    k4.metric("Rủi ro License", f"{len(df_lic[df_lic['used_quantity'] > df_lic['total_quantity']])}", delta_color="inverse")

    st.markdown("---")

    # --- 5. MAIN CONTENT TABS ---
    tab_ai, tab_org, tab_lic, tab_sys = st.tabs(["🚀 AI Predictive", "🌐 Phân bổ Tổ chức", "📊 Tối ưu License", "🏥 Sức khỏe Data"])

    with tab_ai:
        c_left, c_right = st.columns([1.2, 0.8], gap="large")
        with c_left:
            st.markdown("#### 🛠️ Dự báo bảo trì (AI Prediction)")
            # Lọc df_ai dựa trên các asset_tag đã filter ở sidebar
            df_ai_filtered = df_ai[df_ai['asset_tag'].isin(df_filtered['asset_tag'])]
            
            high_risk = df_ai_filtered[df_ai_filtered['risk_score'] > 0.5].sort_values('risk_score', ascending=False)
            st.dataframe(
                high_risk[['asset_tag', 'Type Label', 'risk_score', 'm_count']],
                column_config={
                    "risk_score": st.column_config.ProgressColumn("Xác suất sự cố", format="%.0f%%", min_value=0, max_value=1),
                    "Type Label": "Loại thiết bị",
                    "m_count": "Lượt sửa"
                }, use_container_width=True, hide_index=True
            )
        with c_right:
            st.markdown("#### 💰 Phân tích khấu hao")
            if not df_ai_filtered.empty:
                fig_risk = px.scatter(df_ai_filtered, x="age_days", y="risk_score", color="Type Label",
                                     size="m_count", hover_name="asset_tag", template="plotly_white")
                st.plotly_chart(fig_risk, use_container_width=True)
            else:
                st.caption("Không có dữ liệu rủi ro cho bộ lọc này.")

    with tab_org:
        st.markdown("#### 🏛️ Cơ cấu Tài sản đa tầng")
        if not df_filtered.empty:
            col_sun, col_bar = st.columns([1, 1])
            with col_sun:
                fig_sun = px.sunburst(df_filtered, path=['branch', 'department', 'Type Label'], 
                                     color='branch', color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_sun, use_container_width=True)
            with col_bar:
                branch_data = df_filtered.groupby(['branch', 'status']).size().reset_index(name='Số lượng')
                fig_branch = px.bar(branch_data, x='branch', y='Số lượng', color='status', barmode='group')
                st.plotly_chart(fig_branch, use_container_width=True)
        else:
            st.info("Vui lòng chọn ít nhất một chi nhánh để xem thống kê.")

    with tab_lic:
        if not df_lic.empty:
            df_lic['util_rate'] = (df_lic['used_quantity'] / df_lic['total_quantity'] * 100)
            fig_lic = px.bar(df_lic, x='name', y='util_rate', color='util_rate', color_continuous_scale="RdYlGn",
                             labels={'util_rate': 'Tỷ lệ sử dụng (%)', 'name': 'Phần mềm'})
            st.plotly_chart(fig_lic, use_container_width=True)

    with tab_sys:
        st.success("✅ Hệ thống Supabase & AI Engine đang vận hành bình thường.")
        st.info(f"Phạm vi dữ liệu: {len(df_filtered)} / {len(df_master)} tài sản.")

    # --- 6. ADMIN TOOLS ---
    if st.session_state.get('role') == 'admin':
        with st.expander("🛠️ Admin Debug Console"):
            st.json(ai_metrics)
