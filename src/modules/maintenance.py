import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

def render_maintenance(supabase):
    today = date.today()
    st.markdown('<h1 style="font-weight: 700;">🛠️ Quản lý Bảo trì theo Đơn vị</h1>', unsafe_allow_html=True)

    # --- 1. TRUY VẤN DỮ LIỆU PHÂN CẤP (JOIN ASSETS & STAFF) ---
    # Ta lấy asset_tag từ assets và department, branch từ staff thông qua assigned_to_code
    # Lưu ý: Cú pháp Supabase join qua cột không phải Primary Key cần khai báo rõ
    assets_res = supabase.table("assets").select("""
        id, 
        asset_tag, 
        assigned_to_code,
        staff!assets_assigned_to_code_fkey (
            department,
            branch
        )
    """).execute()
    
    # Chuyển dữ liệu về DataFrame và làm phẳng (flatten)
    if assets_res.data:
        raw_df = pd.DataFrame(assets_res.data)
        # Trích xuất dữ liệu từ cột object 'staff'
        raw_df['department'] = raw_df['staff'].apply(lambda x: x['department'] if x else "Chưa cấp phát")
        raw_df['branch'] = raw_df['staff'].apply(lambda x: x['branch'] if x else "N/A")
        df_assets = raw_df.drop(columns=['staff'])
    else:
        df_assets = pd.DataFrame()

    # --- 2. GIAO DIỆN LỌC PHÂN CẤP ---
    with st.expander("➕ Ghi nhận bảo trì mới", expanded=True):
        with st.form("maint_form_fixed", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            
            with c1:
                branches = sorted(df_assets['branch'].unique().tolist()) if not df_assets.empty else []
                sel_branch = st.selectbox("📍 Chi nhánh", options=["Tất cả"] + branches)
            
            with c2:
                dep_mask = df_assets['branch'] == sel_branch if sel_branch != "Tất cả" else [True]*len(df_assets)
                deps = sorted(df_assets[dep_mask]['department'].unique().tolist()) if not df_assets.empty else []
                sel_dep = st.selectbox("🏢 Phòng ban", options=["Tất cả"] + deps)

            with c3:
                # Lọc mã máy cuối cùng
                final_mask = pd.Series([True] * len(df_assets))
                if sel_branch != "Tất cả": final_mask &= (df_assets['branch'] == sel_branch)
                if sel_dep != "Tất cả": final_mask &= (df_assets['department'] == sel_dep)
                
                valid_assets = df_assets[final_mask]
                asset_dict = {row['asset_tag']: row['id'] for _, row in valid_assets.iterrows()}
                sel_asset_tag = st.selectbox("💻 Mã máy", options=list(asset_dict.keys()))

            st.markdown("---")
            col_a, col_b, col_c = st.columns(3)
            a_type = col_a.selectbox("Loại hình", ["Vệ sinh", "Sửa chữa", "Nâng cấp", "Thay thế"])
            p_date = col_b.date_input("Ngày thực hiện", value=today)
            cost = col_c.number_input("Chi phí (VNĐ)", min_value=0, step=50000)
            
            desc = st.text_area("Nội dung chi tiết")
            n_date = p_date + timedelta(days=180)

            if st.form_submit_button("Lưu nhật ký bảo trì", type="primary", use_container_width=True):
                if sel_asset_tag:
                    try:
                        data = {
                            "asset_id": asset_dict[sel_asset_tag],
                            "action_type": a_type,
                            "description": desc,
                            "performed_at": str(p_date),
                            "cost": cost,
                            "next_scheduled_date": str(n_date)
                        }
                        supabase.table("maintenance_log").insert(data).execute()
                        st.success(f"✅ Đã lưu bảo trì cho {sel_asset_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

    # --- 3. HIỂN THỊ LỊCH SỬ ---
    st.markdown("### 📜 Lịch sử bảo trì hệ thống")
    log_res = supabase.table("maintenance_log").select("""
        performed_at, action_type, description, cost,
        assets!fk_assets (
            asset_tag,
            staff!assets_assigned_to_code_fkey (department, branch)
        )
    """).order("performed_at", desc=True).limit(15).execute()

    if log_res.data:
        logs = []
        for item in log_res.data:
            asset_info = item.get('assets', {})
            staff_info = asset_info.get('staff', {}) if asset_info else {}
            logs.append({
                "Ngày": item['performed_at'],
                "Chi nhánh": staff_info.get('branch', 'N/A'),
                "Phòng": staff_info.get('department', 'N/A'),
                "Mã máy": asset_info.get('asset_tag', 'N/A'),
                "Loại hình": item['action_type'],
                "Chi phí": f"{item['cost']:,} VNĐ"
            })
        st.table(logs)
