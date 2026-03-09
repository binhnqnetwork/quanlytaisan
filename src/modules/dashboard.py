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
        # 1. Truy vấn dữ liệu liên kết từ bảng assets
        # Lấy thêm thông tin Specs để hỗ trợ IT Support nhanh
        res = supabase.table("assets").select("asset_tag, assigned_to_code, department, software_list, specs, type").execute()
        df_usage = pd.DataFrame(res.data)

        if not df_usage.empty:
            # 2. Bộ lọc tìm kiếm (Search Bar) - Phong cách Apple
            search_col1, search_col2 = st.columns([2, 1])
            with search_col1:
                search_term = st.text_input("🔍 Tìm kiếm theo Mã NV, Tên phần mềm hoặc Phòng ban...", placeholder="Ví dụ: Photoshop, 10438, Marketing...")
            with search_col2:
                filter_type = st.multiselect("Lọc loại thiết bị", options=df_usage['type'].unique(), default=df_usage['type'].unique())

            # 3. Xử lý Logic tìm kiếm
            df_display = df_usage[df_usage['type'].isin(filter_type)].copy()
            
            if search_term:
                # Tìm kiếm "mềm" (không phân biệt hoa thường) trên tất cả các cột quan trọng
                mask = (
                    df_display['assigned_to_code'].astype(str).str.contains(search_term, case=False) |
                    df_display['software_list'].str.contains(search_term, case=False, na=False) |
                    df_display['department'].str.contains(search_term, case=False, na=False) |
                    df_display['asset_tag'].str.contains(search_term, case=False)
                )
                df_display = df_display[mask]

            # 4. Hiển thị bảng dữ liệu rực rỡ
            st.write(f"Tìm thấy **{len(df_display)}** kết quả phù hợp.")
            
            # Format lại bảng để chuyên nghiệp hơn
            st.dataframe(
                df_display.rename(columns={
                    'asset_tag': 'Mã Máy',
                    'assigned_to_code': 'Mã Nhân Viên',
                    'department': 'Phòng Ban',
                    'software_list': 'Bản quyền đang dùng',
                    'specs': 'Cấu hình chi tiết',
                    'type': 'Loại máy'
                }),
                use_container_width=True,
                column_config={
                    "Bản quyền đang dùng": st.column_config.TextColumn(width="large"),
                    "Cấu hình chi tiết": st.column_config.TextColumn(width="medium")
                }
            )

            # 5. Gợi ý hành động (Action Tool)
            if not df_display.empty and search_term:
                st.info(f"💡 Mẹo: Bạn đang xem danh sách phần mềm được cấp cho các nhân sự khớp với từ khóa '{search_term}'.")
        else:
            st.info("👋 Hệ thống chưa ghi nhận dữ liệu cấp phát. Hãy cập nhật cột 'software_list' trong tab Kho.")

    except Exception as e:
        st.error(f"❌ Lỗi truy xuất dữ liệu chi tiết: {e}")
