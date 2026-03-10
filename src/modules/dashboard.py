import streamlit as st
import pandas as pd
import plotly.express as px
from . import ai_engine

def render_dashboard(supabase):
    st.header("🏢 Enterprise Asset Intelligence")

    try:
        # 1. TẢI DỮ LIỆU
        res_assets = supabase.table("assets").select("*").execute()
        res_staff = supabase.table("staff").select("*").execute()
        res_lic = supabase.table("licenses").select("*").execute()
        res_maint = supabase.table("maintenance_log").select("*").execute()

        df_assets = pd.DataFrame(res_assets.data)
        df_staff = pd.DataFrame(res_staff.data)
        
        if df_assets.empty:
            st.warning("⚠️ Không có dữ liệu tài sản.")
            return

        # -------------------------------------------------
        # 2. CHUẨN HÓA & XỬ LÝ NULL (SỬA LỖI FULL_NAME)
        # -------------------------------------------------
        # Bước A: Ép kiểu chuỗi và xử lý khoảng trắng, xử lý giá trị null thành chuỗi trống
        df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).replace('None', '').replace('nan', '').str.strip()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()

        # Bước B: Thực hiện Merge an toàn
        df_merged = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )

        # Bước C: "Cấp cứu" cột full_name nếu merge không ra kết quả nào khớp
        if 'full_name' not in df_merged.columns:
            df_merged['full_name'] = "Chưa xác định"
        if 'branch' not in df_merged.columns:
            df_merged['branch'] = "Hệ thống"
        if 'department' not in df_merged.columns:
            df_merged['department'] = "Kho"

        # Bước D: Điền giá trị cho các dòng trống (như Server hoặc máy trong kho)
        df_merged['full_name'] = df_merged['full_name'].fillna("Hệ thống / Trong kho")
        df_merged['branch'] = df_merged['branch'].fillna("Văn phòng")
        df_merged['department'] = df_merged['department'].fillna("Hạ tầng")

        # -------------------------------------------------
        # 3. BỘ LỌC TOÀN CỤC (SIDEBAR)
        # -------------------------------------------------
        with st.sidebar:
            st.divider()
            st.subheader("🛠️ Bộ lọc Enterprise")
            
            # Lấy list unique an toàn
            def get_unique_list(df, col):
                return ["Tất cả"] + sorted([str(x) for x in df[col].unique() if x and x != 'nan'])

            sel_branch = st.selectbox("Chi nhánh", get_unique_list(df_merged, 'branch'))
            sel_dept = st.selectbox("Phòng ban", get_unique_list(df_merged, 'department'))
            sel_status = st.selectbox("Trạng thái", ["Tất cả"] + sorted(df_merged['status'].unique().tolist()))

        # -------------------------------------------------
        # 4. TÌM KIẾM & DRILL-DOWN
        # -------------------------------------------------
        search_query = st.text_input("🔍 Tìm nhanh Asset (Mã máy, Tên nhân viên...)", placeholder="Ví dụ: PC0001, Quang Bình...")

        # Áp dụng Filter
        mask = pd.Series([True] * len(df_merged))
        if sel_branch != "Tất cả": mask &= (df_merged['branch'] == sel_branch)
        if sel_dept != "Tất cả": mask &= (df_merged['department'] == sel_dept)
        if sel_status != "Tất cả": mask &= (df_merged['status'] == sel_status)
        
        if search_query:
            search_mask = (
                df_merged['asset_tag'].str.contains(search_query, case=False, na=False) | 
                df_merged['full_name'].str.contains(search_query, case=False, na=False) |
                df_merged['assigned_to_code'].str.contains(search_query, case=False, na=False)
            )
            mask &= search_mask

        df_filtered = df_merged[mask]

        # -------------------------------------------------
        # 5. GỌI AI ENGINE & HIỂN THỊ KPI
        # -------------------------------------------------
        df_lic = pd.DataFrame(res_lic.data)
        df_maint = pd.DataFrame(res_maint.data)
        
        # Đảm bảo ai_engine nhận được dữ liệu sạch
        metrics, df_ai, lic_ai, b_stats, d_stats, u_stats = ai_engine.calculate_ai_metrics(
            df_filtered, df_maint, df_lic, df_staff
        )

        st.markdown("---")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Thiết bị hiển thị", len(df_filtered))
        k2.metric("🚨 Nguy cấp", metrics.get("critical_assets", 0))
        k3.metric("🔑 Lỗi License", metrics.get("license_alerts", 0))
        k4.metric("🛠️ MTTR (Avg)", metrics.get("mttr", "N/A"))

        # Pie Chart và Bảng Chi tiết
        st.markdown("---")
        c1, c2 = st.columns([6, 4])
        with c1:
            st.subheader("📊 Mức độ rủi ro")
            fig = px.pie(df_ai, names='risk_level', hole=0.5,
                         color='risk_level', color_discrete_map={
                             "🔴 Nguy cấp": "#FF4B4B", "🟠 Cao": "#FFA500", "🟢 Thấp": "#28A745"
                         })
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("📋 Danh sách Chi tiết")
            st.dataframe(
                df_ai[['asset_tag', 'full_name', 'risk_level']].rename(columns={
                    'asset_tag': 'Mã máy', 'full_name': 'Người giữ', 'risk_level': 'Rủi ro'
                }), use_container_width=True, hide_index=True, height=400
            )

    except Exception as e:
        st.error(f"❌ Lỗi Dashboard: {str(e)}")

def render_usage_details(supabase):
    render_dashboard(supabase)
