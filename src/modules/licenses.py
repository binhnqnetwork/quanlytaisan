import streamlit as st
import pandas as pd
from datetime import datetime

def render_licenses(supabase):
    # --- 1. GIAO DIỆN CHUẨN APPLE ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .apple-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #d2d2d7;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .metric-label { color: #86868b; font-size: 14px; font-weight: 500; }
        .metric-value { font-size: 24px; font-weight: 600; color: #1d1d1f; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)

    # --- 2. TRUY VẤN DỮ LIỆU ---
    res = supabase.table("licenses").select("*").order("name").execute()
    
    # Khởi tạo DataFrame an toàn
    if res.data:
        df = pd.DataFrame(res.data)
        # Ép kiểu và xử lý dữ liệu trống
        df['total_quantity'] = df['total_quantity'].fillna(0).astype(int)
        df['used_quantity'] = df['used_quantity'].fillna(0).astype(int)
        df['alert_threshold'] = df['alert_threshold'].fillna(5).astype(int)
        df['Remaining'] = df['total_quantity'] - df['used_quantity']
    else:
        df = pd.DataFrame(columns=['name', 'total_quantity', 'used_quantity', 'Remaining', 'expiry_date', 'alert_threshold'])

    # --- 3. QUICK STATS (KPIs) ---
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="apple-card"><p class="metric-label">Tổng loại phần mềm</p><p class="metric-value">{len(df)}</p></div>', unsafe_allow_html=True)
        with c2:
            total_lic = df['total_quantity'].sum()
            st.markdown(f'<div class="apple-card"><p class="metric-label">Tổng số bản quyền</p><p class="metric-value">{total_lic}</p></div>', unsafe_allow_html=True)
        with c3:
            low_stock_count = len(df[df['Remaining'] <= df['alert_threshold']])
            st.markdown(f'<div class="apple-card"><p class="metric-label">Sắp hết hạn/số lượng</p><p class="metric-value" style="color: #ff3b30;">{low_stock_count}</p></div>', unsafe_allow_html=True)
        with c4:
            usage_rate = (df['used_quantity'].sum() / total_lic * 100) if total_lic > 0 else 0
            st.markdown(f'<div class="apple-card"><p class="metric-label">Tỷ lệ sử dụng</p><p class="metric-value">{usage_rate:.1f}%</p></div>', unsafe_allow_html=True)

    # --- 4. FORM NHẬP LIỆU (OPTIMIZED) ---
    with st.expander("＋ Quản lý kho bản quyền (Thêm/Cập nhật)"):
        with st.form("add_lic_enterprise", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Tên phần mềm", placeholder="VD: Adobe Creative Cloud")
            provider = col2.text_input("Nhà cung cấp", placeholder="VD: PACISOFT")
            
            c1, c2, c3 = st.columns(3)
            total = c1.number_input("Tổng số lượng cấp", min_value=1, step=1)
            threshold = c2.number_input("Ngưỡng cảnh báo (Min)", min_value=0, value=5)
            expiry = c3.date_input("Ngày hết hạn hạn")
            
            if st.form_submit_button("Xác nhận Lưu/Cập nhật"):
                if name:
                    # Sử dụng upsert với on_conflict để tránh lỗi trùng lặp
                    try:
                        supabase.table("licenses").upsert({
                            "name": name.strip(),
                            "total_quantity": total,
                            "expiry_date": str(expiry),
                            "provider": provider,
                            "alert_threshold": threshold
                        }, on_conflict="name").execute()
                        st.success(f"Đã lưu thông tin {name}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi hệ thống: {e}")
                else:
                    st.warning("Vui lòng nhập tên phần mềm.")

    # --- 5. BẢNG DỮ LIỆU & CẢNH BÁO ---
    if not df.empty:
        st.markdown("### 📋 Danh sách bản quyền chi tiết")
        
        # Cảnh báo thông minh
        low_stock = df[df['Remaining'] <= df['alert_threshold']]
        for _, row in low_stock.iterrows():
            st.warning(f"🚨 **{row['name']}** đang ở mức báo động! Còn lại: **{row['Remaining']}** bản. (Hạn: {row['expiry_date']})")

        # Hiển thị bảng dữ liệu
        st.markdown('<div class="apple-card">', unsafe_allow_html=True)
        
        # Tạo cột trạng thái trực quan
        df['Tình trạng'] = df.apply(lambda x: "🔴 Cần mua thêm" if x['Remaining'] <= x['alert_threshold'] else "🟢 Sẵn sàng", axis=1)
        
        st.dataframe(
            df[['name', 'total_quantity', 'used_quantity', 'Remaining', 'expiry_date', 'Tình trạng']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "name": st.column_config.TextColumn("Tên phần mềm", width="large"),
                "total_quantity": "Tổng",
                "used_quantity": "Đã gán",
                "Remaining": st.column_config.ProgressColumn(
                    "Khả dụng",
                    min_value=0,
                    max_value=int(df['total_quantity'].max()),
                    format="%d"
                ),
                "expiry_date": st.column_config.DateColumn("Hết hạn"),
                "Tình trạng": st.column_config.TextColumn("Trạng thái")
            }
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Nút xóa (Optionally)
        with st.expander("🗑️ Khu vực xóa dữ liệu"):
            del_name = st.selectbox("Chọn phần mềm muốn xóa", ["-- Chọn --"] + df['name'].tolist())
            if st.button("Xóa vĩnh viễn", type="secondary"):
                if del_name != "-- Chọn --":
                    supabase.table("licenses").delete().eq("name", del_name).execute()
                    st.success(f"Đã xóa {del_name}")
                    st.rerun()
    else:
        st.info("Chưa có dữ liệu bản quyền. Hãy thêm phần mềm đầu tiên của bạn!")
