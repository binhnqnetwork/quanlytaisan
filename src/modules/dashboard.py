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
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff)
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
        # 1. TRUY VẤN DỮ LIỆU TỪ 2 BẢNG
        # Lấy dữ liệu Assets
        res_assets = supabase.table("assets").select(
            "asset_tag, assigned_to_code, software_list, status"
        ).execute()
        df_assets = pd.DataFrame(res_assets.data)

        # Lấy dữ liệu Staff (Nhân viên)
        res_staff = supabase.table("staff").select(
            "employee_code, full_name, department, branch"
        ).execute()
        df_staff = pd.DataFrame(res_staff.data)

        if not df_assets.empty and not df_staff.empty:
            # 2. XỬ LÝ NỐI DỮ LIỆU (JOIN)
            # Khớp assigned_to_code của assets với employee_code của staff
            df_final = pd.merge(
                df_assets, 
                df_staff, 
                left_on='assigned_to_code', 
                right_on='employee_code', 
                how='left'
            )

            # Làm sạch dữ liệu hiển thị
            df_final['software_display'] = df_final['software_list'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) and len(x) > 0 else "Trống"
            )
            
            # Nếu nhân viên null (máy trong kho), hiển thị là "Chưa cấp phát"
            df_final['full_name'] = df_final['full_name'].fillna("Hệ thống / Trong kho")
            df_final['department'] = df_final['department'].fillna("-")

            # 3. GIAO DIỆN BỘ LỌC
            search_col1, search_col2 = st.columns([2, 1])
            with search_col1:
                search_term = st.text_input("🔍 Tìm theo Tên, Mã NV, Phòng ban hoặc Phần mềm...", placeholder="Ví dụ: Photoshop, Hạnh, IT...")
            with search_col2:
                # Lọc theo Chi nhánh từ bảng staff
                branches = [b for b in df_final['branch'].unique() if b is not None]
                branch_filter = st.multiselect("Lọc theo Chi nhánh", options=branches, default=branches)

            # 4. LOGIC TÌM KIẾM
            mask = df_final['branch'].isin(branch_filter) | df_final['branch'].isna()
            
            if search_term:
                search_mask = (
                    df_final['full_name'].str.contains(search_term, case=False, na=False) |
                    df_final['assigned_to_code'].astype(str).str.contains(search_term, case=False) |
                    df_final['department'].str.contains(search_term, case=False, na=False) |
                    df_final['software_display'].str.contains(search_term, case=False)
                )
                mask = mask & search_mask
            
            df_display = df_final[mask]

            # 5. HIỂN THỊ BẢNG KẾT QUẢ
            st.write(f"Tìm thấy **{len(df_display)}** kết quả.")
            
            st.dataframe(
                df_display[[
                    'asset_tag', 'assigned_to_code', 'full_name', 
                    'department', 'branch', 'software_display', 'status'
                ]].rename(columns={
                    'asset_tag': 'Mã Máy',
                    'assigned_to_code': 'Mã NV',
                    'full_name': 'Tên Nhân Viên',
                    'department': 'Phòng Ban',
                    'branch': 'Chi Nhánh',
                    'software_display': 'Phần mềm đang cài',
                    'status': 'Trạng thái'
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("⚠️ Không thể tải dữ liệu từ bảng Assets hoặc Staff. Vui lòng kiểm tra lại kết nối.")

    except Exception as e:
        st.error(f"❌ Lỗi xử lý dữ liệu: {e}")
