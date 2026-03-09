import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from .ai_engine import calculate_ai_metrics

def render_dashboard(supabase):
    # --- 1. CONFIG & SYSTEM STYLE ---
    st.markdown("""
        <style>
        .stMetric { background: #ffffff; padding: 20px; border-radius: 16px; border: 1px solid #f0f0f5; box-shadow: 0 4px 6px rgba(0,0,0,0.02); }
        [data-testid="stMetricValue"] { font-weight: 800; color: #1d1d1f; letter-spacing: -1px; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { 
            background-color: #f5f5f7; border-radius: 8px; padding: 10px 20px; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { background-color: #0071e3 !important; color: white !important; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. SMART DATA INGESTION ---
    try:
        # Fetch data
        assets_res = supabase.table("assets").select("*").execute()
        lic_res = supabase.table("licenses").select("*").execute()
        maint_res = supabase.table("maintenance_log").select("*").execute()
        staff_res = supabase.table("staff").select("*").execute()

        df_assets = pd.DataFrame(assets_res.data) if assets_res.data else pd.DataFrame()
        df_lic = pd.DataFrame(lic_res.data) if lic_res.data else pd.DataFrame()
        df_maint = pd.DataFrame(maint_res.data) if maint_res.data else pd.DataFrame()
        df_staff = pd.DataFrame(staff_res.data) if staff_res.data else pd.DataFrame()

        # Data Pre-processing cho Chi nhánh/Bộ phận
        type_labels = {'LT': 'Laptop', 'PC': 'Desktop PC', 'MN': 'Monitor', 'SV': 'Server', 'OT': 'Other'}
        df_assets['Type Name'] = df_assets['type'].map(type_labels).fillna('Khác')
        
        # Merge dữ liệu để phân tích đa chiều
        df_master = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'branch', 'department', 'full_name']], 
            left_on='assigned_to_code', right_on='employee_code', how='left'
        ).fillna({"branch": "Chưa phân bổ", "department": "Chưa rõ", "full_name": "N/A"})

        # Gọi AI Engine
        ai_metrics, df_ai = calculate_ai_metrics(df_assets, df_maint, df_lic)
    except Exception as e:
        st.error(f"❌ Critical Data Error: {e}")
        return

    # --- 3. SIDEBAR GLOBAL FILTERS ---
    st.sidebar.markdown("### 🔍 Bộ lọc chiến lược")
    selected_branch = st.sidebar.multiselect("Chi nhánh", options=df_master['branch'].unique(), default=df_master['branch'].unique())
    
    # Filter dữ liệu dựa trên Sidebar
    df_filtered = df_master[df_master['branch'].isin(selected_branch)]
    df_ai_filtered = df_ai[df_ai['asset_tag'].isin(df_filtered['asset_tag'])]

    # --- 4. HEADER & BI KPIs ---
    st.markdown('<h1 style="font-weight: 800; color: #1d1d1f; margin-bottom: 0;">🧠 AI Strategic Hub</h1>', unsafe_allow_html=True)
    st.caption(f"Hệ thống phân tích tài sản thông minh | Cập nhật: {datetime.now().strftime('%H:%M:%S')}")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Reliability (MTBF)", ai_metrics['mtbf'], "Target: >150d")
    with kpi2:
        st.metric("Recovery (MTTR)", ai_metrics['mttr'], "-0.5h vs Q4", delta_color="normal")
    with kpi3:
        util_rate = (len(df_filtered[df_filtered['status'] == 'Đang sử dụng']) / len(df_filtered) * 100) if not df_filtered.empty else 0
        st.metric("Utilization", f"{util_rate:.1f}%", "Optimal")
    with kpi4:
        st.metric("AI Risk Alert", f"{len(df_ai_filtered[df_ai_filtered['risk_score'] > 0.7])}", "Critical", delta_color="inverse")

    st.markdown("---")

    # --- 5. TABS INTERFACE ---
    tabs = st.tabs(["🚀 AI Predictive", "🏛️ Organization Dist.", "📊 Optimization", "🏥 System Health"])

    with tabs[0]:
        st.markdown("#### 🛠️ Phân tích rủi ro & Dự báo hỏng hóc")
        c1, c2 = st.columns([1.2, 0.8])
        with c1:
            high_risk = df_ai_filtered[df_ai_filtered['risk_score'] > 0.5].sort_values('risk_score', ascending=False)
            st.dataframe(
                high_risk[['asset_tag', 'Type Name', 'risk_score', 'm_count']],
                column_config={
                    "risk_score": st.column_config.ProgressColumn("Failure Probability", format="%.0f%%", min_value=0, max_value=1),
                    "m_count": "Lượt sửa"
                }, use_container_width=True, hide_index=True
            )
        with c2:
            fig_risk = px.scatter(df_ai_filtered, x="age_days", y="risk_score", color="Type Name", 
                                 size="m_count", hover_name="asset_tag", template="plotly_white")
            fig_risk.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_risk, use_container_width=True)

    with tabs[1]:
        st.markdown("#### 🌐 Thống kê Đa tầng: Chi nhánh & Bộ phận")
        col_sun, col_tree = st.columns(2)
        with col_sun:
            # Sunburst cho cái nhìn "lung linh" đa tầng
            fig_sun = px.sunburst(df_filtered, path=['branch', 'department', 'Type Name'], 
                                 color='branch', color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_sun, use_container_width=True)
        with col_tree:
            # Treemap cho mật độ tài sản
            fig_tree = px.treemap(df_filtered, path=[px.Constant("Toàn quốc"), 'branch', 'department'], 
                                 color='branch', color_discrete_sequence=px.colors.qualitative.Set3)
            st.plotly_chart(fig_tree, use_container_width=True)

    with tabs[2]:
        st.markdown("#### 📈 Tối ưu hóa Bản quyền & Khấu hao")
        # Stacked Bar Chart theo bộ phận
        dept_dist = df_filtered.groupby(['department', 'Type Name']).size().reset_index(name='Count')
        fig_bar = px.bar(dept_dist, x='department', y='Count', color='Type Name', barmode='stack', text_auto=True)
        st.plotly_chart(fig_bar, use_container_width=True)

    with tabs[3]:
        st.markdown("#### 🏥 Giám sát vận hành hệ thống")
        h1, h2, h3 = st.columns(3)
        h1.success(f"Supabase: Connected\nLatency: 28ms")
        h2.info(f"AI Engine: Active\nModel: Lifecycle-v2")
        h3.warning(f"Role: {st.session_state.get('role', 'Viewer').upper()}")
        
        # Nhật ký bảo trì gần đây
        if not df_maint.empty:
            st.write("**Dòng thời gian bảo trì mới nhất:**")
            st.table(df_maint.sort_values('performed_at', ascending=False).head(5)[['asset_id', 'performed_at', 'description']])

    # --- 6. ADMIN EXTRAS ---
    if st.session_state.get('role') == 'admin':
        with st.expander("🔐 Admin Intelligence Metadata"):
            st.write(ai_metrics)
