import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

def render_maintenance(supabase):
    today = date.today()
    st.markdown('<h1 style="font-weight: 700;">🛠️ Nhật ký Bảo trì Chuyên nghiệp</h1>', unsafe_allow_html=True)

    # --- 1. TRUY VẤN & CHUẨN HÓA DỮ LIỆU GỐC ---
    @st.cache_data(ttl=600)
    def get_full_asset_data():
        # Join assets -> staff để lấy Branch, Dept, Full Name
        res = supabase.table("assets").select("""
            id, asset_tag, assigned_to_code,
            staff!assets_assigned_to_code_fkey (
                full_name,
                department,
                branch
            )
        """).execute()
        
        if not res.data: return pd.DataFrame()
        
        data = []
        for item in res.data:
            s = item.get('staff') or {}
            data.append({
                "id": item['id'],
                "asset_tag": item['asset_tag'],
                "employee_code": item['assigned_to_code'],
                "full_name": s.get('full_name', 'Chưa cấp phát'),
                "department": s.get('department', 'N/A'),
                "branch": s.get('branch', 'N/A')
            })
        return pd.DataFrame(data)

    df_assets = get_full_asset_data()

    if df_assets.empty:
        st.warning("⚠️ Không có dữ liệu thiết bị.")
        return

    # --- 2. FORM GHI NHẬN VỚI LỌC LIÊN KẾT (CASCADING) ---
    with st.expander("➕ Ghi nhận bảo trì mới", expanded=True):
        # 2.1. Tìm kiếm nhanh theo tên nhân viên (Vấn đề 3)
        search_name = st.text_input("🔍 Tìm nhanh theo Tên nhân viên", placeholder="Nhập tên nhân viên để lọc...")
        
        filtered_df = df_assets.copy()
        if search_name:
            filtered_df = filtered_df[filtered_df['full_name'].str.contains(search_name, case=False, na=False)]

        with st.form("maint_form_v3", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            # Vấn đề 1: Lọc liên kết Chi nhánh -> Phòng ban -> Mã máy
            with col1:
                branches = sorted(filtered_df['branch'].unique().tolist())
                sel_branch = st.selectbox("📍 Chi nhánh", options=["Tất cả"] + branches)
            
            with col2:
                # Lọc phòng ban dựa trên chi nhánh (Vấn đề 1)
                temp_df = filtered_df.copy()
                if sel_branch != "Tất cả":
                    temp_df = temp_df[temp_df['branch'] == sel_branch]
                
                deps = sorted(temp_df['department'].unique().tolist())
                sel_dep = st.selectbox("🏢 Phòng ban", options=["Tất cả"] + deps)

            with col3:
                # Lọc mã máy dựa trên chi nhánh & phòng ban (Vấn đề 1)
                final_filter_df = temp_df.copy()
                if sel_dep != "Tất cả":
                    final_filter_df = final_filter_df[final_filter_df['department'] == sel_dep]
                
                # Hiển thị Tên nhân viên đính kèm Mã máy (Vấn đề 2)
                # Tạo label: "PC0001 - Nguyễn Văn A"
                final_filter_df['display_label'] = final_filter_df['asset_tag'] + " - " + final_filter_df['full_name']
                
                asset_options = final_filter_df['display_label'].tolist()
                sel_display = st.selectbox("💻 Chọn Thiết bị (Mã máy - Tên NV)", options=asset_options)
                
                # Lấy lại ID thực tế từ label đã chọn
                selected_asset_id = None
                if sel_display:
                    selected_asset_tag = sel_display.split(" - ")[0]
                    selected_asset_id = final_filter_df[final_filter_df['asset_tag'] == selected_asset_tag]['id'].values[0]

            st.markdown("---")
            c_a, c_b, c_c = st.columns(3)
            action = c_a.selectbox("Loại hình", ["Vệ sinh", "Sửa chữa", "Nâng cấp", "Thay mới"])
            p_date = c_b.date_input("Ngày thực hiện", value=today)
            cost = c_c.number_input("Chi phí (VNĐ)", min_value=0, step=50000, format="%d")
            
            desc = st.text_area("Nội dung chi tiết (Ví dụ: Thay ổ cứng SSD 512GB, vệ sinh máy thổi bụi...)")

            if st.form_submit_button("💾 LƯU NHẬT KÝ BẢO TRÌ", type="primary", use_container_width=True):
                if not selected_asset_id:
                    st.error("Vui lòng chọn thiết bị!")
                else:
                    try:
                        new_log = {
                            "asset_id": int(selected_asset_id),
                            "action_type": action,
                            "description": desc,
                            "performed_at": str(p_date),
                            "cost": cost,
                            "next_scheduled_date": str(p_date + timedelta(days=180))
                        }
                        supabase.table("maintenance_log").insert(new_log).execute()
                        st.success(f"✅ Đã ghi nhận bảo trì thành công!")
                        st.balloons()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi khi lưu: {str(e)}")

    # --- 3. HIỂN THỊ LỊCH SỬ (VỚI ĐỦ THÔNG TIN NHÂN VIÊN) ---
    st.markdown("### 📜 Lịch sử vận hành gần đây")
    
    # Query join 3 tầng để hiển thị bảng lịch sử
    log_res = supabase.table("maintenance_log").select("""
        performed_at, action_type, description, cost,
        assets!fk_assets (
            asset_tag,
            staff!assets_assigned_to_code_fkey (full_name, department, branch)
        )
    """).order("performed_at", desc=True).limit(20).execute()

    if log_res.data:
        history = []
        for l in log_res.data:
            a = l.get('assets') or {}
            s = a.get('staff') or {}
            history.append({
                "Ngày": l['performed_at'],
                "Nhân viên": s.get('full_name', 'N/A'),
                "Mã máy": a.get('asset_tag', 'N/A'),
                "Phòng ban": s.get('department', 'N/A'),
                "Loại hình": l['action_type'],
                "Chi phí": l['cost'],
                "Nội dung": l['description']
            })
        
        df_history = pd.DataFrame(history)
        st.dataframe(
            df_history,
            column_config={
                "Chi phí": st.column_config.NumberColumn("Chi phí", format="%d VNĐ"),
                "Ngày": st.column_config.DateColumn("Ngày")
            },
            use_container_width=True,
            hide_index=True
        )
