import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
# Đảm bảo đường dẫn import chính xác với cấu trúc thư mục của bạn
from .ai_engine import calculate_ai_metrics 

def render_dashboard(supabase):
    # --- 1. SETTINGS & ENTERPRISE UI (APPLE STYLE) ---
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
        # Fetch dữ liệu master
        assets_res = supabase.table("assets").select("*").execute()
        lic_res = supabase.table("licenses").select("*").execute()
        maint_res = supabase.table("maintenance_log").select("*").execute()
        staff_res = supabase.table("staff").select("employee_code", "full_name", "branch", "department").execute()

        df_assets = pd.DataFrame(assets_res.data) if assets_res.data else pd.DataFrame()
        df_lic = pd.DataFrame(lic_res.data) if lic_res.data else pd.DataFrame()
        df_maint = pd.DataFrame(maint_res.data) if maint_res.data else pd.DataFrame()
        df_staff = pd.DataFrame(staff_res.data) if staff_res.data else pd.DataFrame()
        
        if df_assets.empty:
            st.warning("Chưa có dữ liệu tài sản để hiển thị Dashboard.")
            return

        # Chuẩn hóa nhãn thiết bị
        type_labels = {'lt': 'Laptop', 'pc': 'Desktop PC', 'mn': 'Monitor', 'sv': 'Server', 'ot': 'Khác'}
        df_assets['Type Label'] = df_assets['type'].str.lower().map(type_labels).fillna('Khác')

        # --- GỌI ENGINE V2 (NHẬN 3 GIÁ TRỊ) ---
        # Đây là phần fix lỗi "cannot import name" và "too many values to unpack"
        ai_metrics, df_ai, license_ai = calculate_ai_metrics(df_assets, df_maint, df_lic)
        
        if not df_ai.empty:
            df_ai['Type Label'] = df_ai['type'].str.lower().map(type_labels).fillna('Khác')

        # Merge master data để lọc theo Chi nhánh/Bộ phận
        df_master = pd.merge(
            df_assets, 
            df_staff, 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        ).fillna({"branch": "Chưa phân bổ", "department": "Kho", "full_name": "N/A"})

    except Exception as e:
        st.error(f"Lỗi hệ thống dữ liệu (Chi tiết: {e})")
        return

    # --- 3. SIDEBAR GLOBAL FILTERS ---
    st.sidebar.markdown("## 🔍 Bộ lọc Hệ thống")
    all_branches = sorted(df_master['branch'].unique().tolist())
    selected_branches = st.sidebar.multiselect("📍 Chọn Chi nhánh", options=all_branches, default=all_branches)
    
    df_filtered = df_master[df_master['branch'].isin(selected_branches)]
    
    relevant_depts = sorted(df_filtered['department'].unique().tolist())
    selected_depts = st.sidebar.multiselect("🏢 Chọn Bộ phận", options=relevant_depts, default=relevant_depts)

    df_filtered = df_filtered[df_filtered['department'].isin(selected_depts)]

    # --- 4. HEADER & KPIs (SỬ DỤNG AI_METRICS MỚI) ---
    st.markdown('<h1 style="color: #1d1d1f; font-weight: 800;">🧠 AI Strategic Hub</h1>', unsafe_allow_html=True)
    st.caption(f"Dữ liệu đồng bộ Real-time: {datetime.now().strftime('%H:%M:%S')}")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Độ tin cậy (MTBF)", ai_metrics.get('mtbf', 'N/A'))
    k2.metric("Thời gian sửa (MTTR)", ai_metrics.get('mttr', 'N/A'))
    
    # Hiển thị số máy Critical từ Engine V2
    k3.metric("Thiết bị Rủi ro cao", f"{ai_metrics.get('critical_assets', 0)}", "Cần bảo trì", delta_color="inverse")
    
    # Rủi ro License dựa trên bảng license_ai mới
    lic_risk_count = len(license_ai[license_ai['license_risk'] == 'Critical']) if not license_ai.empty else 0
    k4.metric("Rủi ro License", f"{lic_risk_count}", "Hết hạn/Vượt hạn", delta_color="inverse")

    st.markdown("---")

    # --- 5. MAIN CONTENT TABS ---
    tab_ai, tab_org, tab_lic = st.tabs(["🚀 AI Predictive", "🌐 Phân bổ Tổ chức", "📊 Tối ưu License"])

    with tab_ai:
        c_left, c_right = st.columns([1.2, 0.8], gap="large")
        with c_left:
            st.markdown("#### 🛠️ Dự báo bảo trì (Failure Probability)")
            # Lọc df_ai theo sidebar
            df_ai_filtered = df_ai[df_ai['asset_tag'].isin(df_filtered['asset_tag'])]
            
            if not df_ai_filtered.empty:
                # Sắp xếp theo xác suất hỏng từ cao xuống thấp
                st.dataframe(
                    df_ai_filtered.sort_values('failure_probability', ascending=False),
                    column_config={
                        "failure_probability": st.column_config.ProgressColumn(
                            "Xác suất sự cố", format="%.0f%%", min_value=0, max_value=1
                        ),
                        "risk_level": "Mức độ",
                        "asset_tag": "Mã tài sản",
                        "Type Label": "Loại"
                    }, 
                    hide_index=True, 
                    use_container_width=True,
                    # Chỉ hiện các cột quan trọng
                    column_order=("asset_tag", "Type Label", "risk_level", "failure_probability")
                )
            else:
                st.info("Chưa có dữ liệu phân tích AI.")

        with c_right:
            st.markdown("#### 💰 Risk Score vs Usage Days")
            if not df_ai_filtered.empty:
                fig_risk = px.scatter(df_ai_filtered, x="age_days", y="risk_score", 
                                      color="risk_level", size="m_count",
                                      hover_name="asset_tag", template="plotly_white",
                                      color_discrete_map={"Critical": "#ff3b30", "High": "#ff9500", "Medium": "#ffcc00", "Low": "#34c759"})
                st.plotly_chart(fig_risk, use_container_width=True)

    with tab_org:
        st.markdown("#### 🏛️ Cơ cấu phân bổ thiết bị")
        
        fig_sun = px.sunburst(df_filtered, path=['branch', 'department', 'Type Label'], 
                             color='branch', color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_sun, use_container_width=True)

    with tab_lic:
        st.markdown("#### 📊 Áp lực sử dụng License")
        if not license_ai.empty:
            # Vẽ biểu đồ dựa trên bảng license_ai đã được engine v2 xử lý
            fig_lic = px.bar(license_ai, x='name', y='usage_ratio', color='license_risk',
                             color_discrete_map={"Critical": "#ff3b30", "Warning": "#ff9500", "Healthy": "#34c759"},
                             labels={'usage_ratio': 'Tỷ lệ sử dụng', 'name': 'Phần mềm'})
            fig_lic.add_hline(y=1.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_lic, use_container_width=True)
