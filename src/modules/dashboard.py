import streamlit as st
import pandas as pd
import plotly.express as px
from .ai_engine import calculate_ai_metrics 

def render_dashboard(supabase):
    st.header("📊 Hệ thống Phân tích & Dự báo Tài sản (AI)")
    
    # 1. TẢI DỮ LIỆU TỪ SUPABASE
    try:
        res_assets = supabase.table("assets").select("*").execute()
        df_assets = pd.DataFrame(res_assets.data)

        res_maint = supabase.table("maintenance_log").select("*").execute()
        df_maint = pd.DataFrame(res_maint.data)

        res_lic = supabase.table("licenses").select("*").execute()
        df_lic = pd.DataFrame(res_lic.data)

    except Exception as e:
        st.error(f"❌ Lỗi kết nối cơ sở dữ liệu: {e}")
        return

    # 2. XỬ LÝ AI METRICS
    if not df_assets.empty:
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = calculate_ai_metrics(df_assets, df_maint, df_lic)

        # 3. KPI CARDS
        st.markdown("---")
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        with m_col1: st.metric("⏳ MTBF", metrics["mtbf"])
        with m_col2: st.metric("🛠️ MTTR", metrics["mttr"])
        with m_col3: st.metric("🚨 Nguy cấp", metrics["critical_assets"], delta_color="inverse")
        with m_col4: st.metric("🟠 Rủi ro cao", metrics["high_risk_assets"])
        with m_col5: st.metric("🔑 License", metrics["license_alerts"])

        st.markdown("---")

        # 4. PHÂN TÍCH CHI TIẾT
        col_left, col_right = st.columns([6, 4])

        with col_left:
            st.subheader("📍 Bản đồ Rủi ro theo Chi nhánh")
            fig_branch = px.bar(
                b_stats.reset_index(), 
                x='branch', y='Rủi ro TB', color='Rủi ro TB',
                color_continuous_scale='Reds',
                text_auto='.2f'
            )
            st.plotly_chart(fig_branch, use_container_width=True)

            st.subheader("🔍 Danh sách Tài sản Nguy cấp")
            critical_list = df_ai[df_ai['risk_level'] == "🔴 Nguy cấp"][['asset_tag', 'type', 'assigned_to', 'failure_prob']]
            st.dataframe(critical_list.sort_values('failure_prob', ascending=False), use_container_width=True)

        with col_right:
            st.subheader("🏢 Phân bổ Mức độ Rủi ro")
            # ĐỊNH NGHĨA FIG_PIE TẠI ĐÂY ĐỂ TRÁNH LỖI NAMEERROR
            fig_pie = px.pie(
                df_ai, names='risk_level', 
                color='risk_level',
                color_discrete_map={
                    "🔴 Nguy cấp": "#ff4b4b", "🟠 Cao": "#ffa500",
                    "🟡 Trung bình": "#ffd700", "🟢 Thấp": "#28a745"
                }
            )
            st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("👤 Top 10 User cần lưu ý")
            # Chỉ hiển thị 1 bảng duy nhất, đã đồng bộ tên cột
            st.dataframe(
                u_stats.style.background_gradient(cmap='YlOrRd', subset=['Tổng lượt hỏng', 'Rủi ro Max']),
                use_container_width=True
            )

        # 5. PHÂN TÍCH BẢO TRÌ & LICENSE
        if not lic_ai.empty:
            st.markdown("---")
            st.subheader("🌐 Tình trạng Bản quyền & Phần mềm")
            
            # Kiểm tra tên cột thực tế để tránh lỗi 'not in index'
            available_cols = lic_ai.columns.tolist()
            
            # Xác định cột tên phần mềm (Thử các trường hợp phổ biến)
            name_col = next((c for c in ['software_name', 'name', 'software', 'license_name'] if c in available_cols), None)
            
            risk_licenses = lic_ai[lic_ai['license_risk'] != "✅ Ổn định"]
            
            if not risk_licenses.empty:
                st.warning(f"Có {len(risk_licenses)} phần mềm sắp hết hạn hoặc vượt hạn mức.")
                
                # Chỉ hiển thị các cột thực sự tồn tại
                display_cols = [c for c in [name_col, 'remaining', 'usage_ratio', 'license_risk'] if c is not None and c in available_cols]
                st.table(risk_licenses[display_cols])
            else:
                st.success("Tất cả bản quyền đang ở trạng thái an toàn.")

    else:
        st.info("👋 Chưa có dữ liệu tài sản để phân tích.")
def render_usage_details(supabase):
    st.subheader("👥 Truy xuất Chi tiết Cấp phát License & Nhân sự")
    
    try:
        # 1. TRUY VẤN: Bỏ cột 'department' bị lỗi, thêm các cột thực tế từ bảng của bạn
        res = supabase.table("assets").select(
            "asset_tag, assigned_to_code, software_list, specs, type, status"
        ).execute()
        df_usage = pd.DataFrame(res.data)

        if not df_usage.empty:
            # 2. XỬ LÝ DỮ LIỆU THÔNG MINH (AI Heuristics)
            # Tự tạo cột 'Vùng miền' bằng cách tách chữ cuối sau dấu gạch ngang (PC0001-HCM -> HCM)
            df_usage['region'] = df_usage['asset_tag'].str.split('-').str[-1]
            
            # Làm sạch hiển thị software_list (từ list sang string để dễ nhìn)
            df_usage['software_display'] = df_usage['software_list'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) and len(x) > 0 else "Trống"
            )

            # 3. BỘ LỌC TÌM KIẾM
            search_col1, search_col2 = st.columns([2, 1])
            with search_col1:
                search_term = st.text_input("🔍 Tìm theo Mã NV, Phần mềm (Photoshop, Office...)", placeholder="Ví dụ: 3140 hoặc Photoshop...")
            with search_col2:
                region_filter = st.multiselect("Lọc theo Vùng miền", options=df_usage['region'].unique(), default=df_usage['region'].unique())

            # 4. LOGIC LỌC
            df_display = df_usage[df_usage['region'].isin(region_filter)].copy()
            
            if search_term:
                mask = (
                    df_display['assigned_to_code'].astype(str).str.contains(search_term, case=False) |
                    df_display['software_display'].str.contains(search_term, case=False) |
                    df_display['asset_tag'].str.contains(search_term, case=False)
                )
                df_display = df_display[mask]

            # 5. HIỂN THỊ BẢNG (Đã khớp 100% với DB của bạn)
            st.write(f"Tìm thấy **{len(df_display)}** kết quả.")
            
            st.dataframe(
                df_display[[
                    'asset_tag', 'assigned_to_code', 'region', 
                    'software_display', 'specs', 'status'
                ]].rename(columns={
                    'asset_tag': 'Mã Máy',
                    'assigned_to_code': 'Mã Nhân Viên',
                    'region': 'Vùng miền',
                    'software_display': 'Bản quyền đang dùng',
                    'specs': 'Cấu hình',
                    'status': 'Trạng thái'
                }),
                use_container_width=True
            )

        else:
            st.info("👋 Hệ thống chưa có dữ liệu tài sản.")

    except Exception as e:
        st.error(f"❌ Lỗi cấu trúc bảng: {e}")
