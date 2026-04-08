import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. GIAO DIỆN CHUẨN APPLE (UI/UX) ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .stMetric { background: white; padding: 20px; border-radius: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e5e5e7; }
        [data-testid="stExpander"] { border-radius: 12px; border: 1px solid #d2d2d7; background: white; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU TẬP TRUNG ---
    with st.spinner("Đang đồng bộ kho bản quyền..."):
        res = supabase.table("licenses").select("*").order("name").execute()
        df_raw = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. TIÊU ĐỀ ---
    st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)
    
    if not df_raw.empty:
        # --- 4. XỬ LÝ DỮ LIỆU (FIX LỖI TẠI ĐÂY) ---
        df = df_raw.copy()
        df['total_quantity'] = pd.to_numeric(df['total_quantity'], errors='coerce').fillna(0).astype(int)
        df['used_quantity'] = pd.to_numeric(df['used_quantity'], errors='coerce').fillna(0).astype(int)
        df['remaining'] = df['total_quantity'] - df['used_quantity']
        
        # BƯỚC QUAN TRỌNG: Chuyển đổi chuỗi ngày từ DB sang kiểu date của Python để tương thích với DateColumn
        df['expiry_date'] = pd.to_datetime(df['expiry_date'], errors='coerce').dt.date
        
        today = date.today()
        # Tính toán ngày chênh lệch để phân loại trạng thái
        df['days_diff'] = df['expiry_date'].apply(lambda x: (x - today).days if pd.notnull(x) else 999)
        
        # Phân loại rủi ro cho Metrics
        critical_df = df[(df['remaining'] < 0) | (df['days_diff'] <= 7)]
        warning_df = df[(df['remaining'] == 0) | ((df['days_diff'] > 7) & (df['days_diff'] <= 30))]

        # --- 5. HIỂN THỊ KPI ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tổng phần mềm", len(df))
        col2.metric("Tổng bản quyền", df['total_quantity'].sum())
        col3.metric("⚠️ Rủi ro/Hết hạn", len(critical_df) + len(warning_df), 
                    delta=f"{len(critical_df)} Nghiêm trọng" if len(critical_df) > 0 else None,
                    delta_color="inverse")
        
        usage_rate = (df['used_quantity'].sum() / df['total_quantity'].sum() * 100) if df['total_quantity'].sum() > 0 else 0
        col4.metric("Tỷ lệ lấp đầy", f"{usage_rate:.1f}%")

        # --- 6. DANH SÁCH CHI TIẾT (SMART TABLE) ---
        st.markdown("### 📋 Trạng thái kho License")
        
        def get_status(row):
            if pd.isnull(row['expiry_date']): return "⚪ Không xác định"
            if row['days_diff'] < 0: return "❌ Đã hết hạn"
            if row['days_diff'] <= 30: return "⚠️ Sắp hết hạn"
            if row['remaining'] < 0: return "❗ Dùng quá số lượng"
            return "✅ Ổn định"

        df['Trạng thái'] = df.apply(get_status, axis=1)

        # Sử dụng data_editor với cấu hình cột đã fix
        st.data_editor(
            df[['name', 'total_quantity', 'used_quantity', 'remaining', 'expiry_date', 'Trạng thái']],
            use_container_width=True,
            hide_index=True,
            disabled=True, 
            column_config={
                "name": st.column_config.TextColumn("🏷️ Tên phần mềm"),
                "total_quantity": st.column_config.NumberColumn("🔢 Tổng"),
                "used_quantity": st.column_config.NumberColumn("📤 Đã cấp"),
                "remaining": st.column_config.ProgressColumn(
                    "🟢 Khả dụng", 
                    min_value=0, 
                    max_value=int(df['total_quantity'].max()) if not df.empty else 100,
                    format="%d"
                ),
                # Cột này bây giờ sẽ hoạt động vì dữ liệu đã là kiểu date
                "expiry_date": st.column_config.DateColumn("📅 Hạn dùng", format="DD/MM/YYYY"),
                "Trạng thái": st.column_config.TextColumn("💡 Trạng thái")
            }
        )

        st.markdown("---")

        # --- 7. CÁC THAO TÁC QUẢN TRỊ (Giữ nguyên logic cũ của bạn) ---
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("🔄 Thu hồi License"):
                res_assets = supabase.table("assets").select("id, asset_tag, software_list").execute()
                assets_with_sw = [a for a in res_assets.data if a.get('software_list')]
                if assets_with_sw:
                    with st.form("form_harvest"):
                        selected_asset = st.selectbox("Chọn thiết bị", assets_with_sw, 
                                                     format_func=lambda x: f"{x['asset_tag']} ({len(x['software_list'])} SW)")
                        sw_to_remove = st.multiselect("Phần mềm thu hồi", selected_asset['software_list'])
                        if st.form_submit_button("Xác nhận thu hồi", type="primary"):
                            if sw_to_remove:
                                # Logic update tại đây...
                                new_sw_list = [s for s in selected_asset['software_list'] if s not in sw_to_remove]
                                supabase.table("assets").update({"software_list": new_sw_list}).eq("id", selected_asset['id']).execute()
                                for sw in sw_to_remove:
                                    lic_info = df[df['name'] == sw]
                                    if not lic_info.empty:
                                        new_used = max(0, int(lic_info.iloc[0]['used_quantity']) - 1)
                                        supabase.table("licenses").update({"used_quantity": new_used}).eq("name", sw).execute()
                                st.success("Đã thu hồi thành công!")
                                st.rerun()
                else:
                    st.info("Không có thiết bị giữ license.")

        with c2:
            with st.expander("🗑️ Xóa phần mềm"):
                del_target = st.selectbox("Chọn phần mềm", ["-- Chọn --"] + df['name'].tolist())
                if st.button("Xóa vĩnh viễn", type="secondary", use_container_width=True):
                    if del_target != "-- Chọn --":
                        supabase.table("licenses").delete().eq("name", del_target).execute()
                        st.rerun()

    # --- 8. THÊM MỚI (UPSERT) ---
    with st.expander("➕ Đăng ký / Gia hạn bản quyền"):
        with st.form("form_add_sw"):
            col_a, col_b, col_c = st.columns([2, 1, 1])
            name_in = col_a.text_input("Tên phần mềm")
            qty_in = col_b.number_input("Tổng số lượng", min_value=1, step=1)
            expiry_in = col_c.date_input("Ngày hết hạn")
            if st.form_submit_button("Lưu thông tin"):
                if name_in:
                    supabase.table("licenses").upsert({
                        "name": name_in.strip(),
                        "total_quantity": qty_in,
                        "expiry_date": str(expiry_in)
                    }, on_conflict="name").execute()
                    st.rerun()

    if df_raw.empty:
        st.info("📭 Kho bản quyền đang trống.")
