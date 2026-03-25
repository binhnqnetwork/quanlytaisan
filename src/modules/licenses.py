import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. GIAO DIỆN CHUẨN APPLE ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .apple-card {
            background: #ffffff; border-radius: 16px; padding: 20px;
            border: 1px solid #d2d2d7; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        .metric-label { color: #86868b; font-size: 14px; font-weight: 500; }
        .metric-value { font-size: 24px; font-weight: 600; color: #1d1d1f; }
        .expiry-urgent { color: #ff3b30; font-weight: 700; }
        .expiry-warning { color: #ff9500; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)

    # --- 2. TRUY VẤN & XỬ LÝ DỮ LIỆU THÔNG MINH ---
    res = supabase.table("licenses").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # Chuyển đổi kiểu dữ liệu
        df['total_quantity'] = df['total_quantity'].fillna(0).astype(int)
        df['used_quantity'] = df['used_quantity'].fillna(0).astype(int)
        df['alert_threshold'] = df['alert_threshold'].fillna(5).astype(int)
        df['Remaining'] = df['total_quantity'] - df['used_quantity']
        
        # Xử lý ngày tháng và tính khoảng cách
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        today = date.today()
        df['days_to_expiry'] = df['expiry_date'].apply(lambda x: (x - today).days)

        # ---------------------------------------------------------
        # 3. PHÂN LOẠI TRẠNG THÁI & SẮP XẾP ƯU TIÊN (CORE LOGIC)
        # ---------------------------------------------------------
        def categorize_status(row):
            if row['days_to_expiry'] < 0:
                return 0, "🚫 Đã hết hạn", "urgent"
            if row['days_to_expiry'] <= 30:
                return 1, f"⚠️ Hết hạn sau {row['days_to_expiry']} ngày", "warning"
            if row['Remaining'] <= row['alert_threshold']:
                return 2, "📉 Sắp hết số lượng", "warning"
            return 3, "🟢 Đang hoạt động", "normal"

        # Áp dụng logic phân loại
        status_results = df.apply(categorize_status, axis=1)
        df['sort_priority'] = status_results.apply(lambda x: x[0])
        df['Tình trạng'] = status_results.apply(lambda x: x[1])
        
        # Sắp xếp: Ưu tiên (priority) -> Ngày hết hạn (càng gần càng lên đầu) -> Tên
        df = df.sort_values(by=['sort_priority', 'days_to_expiry', 'name'], ascending=[True, True, True])

    else:
        df = pd.DataFrame()

    # --- 4. QUICK STATS (KPIs) ---
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        total_lic = df['total_quantity'].sum()
        with c1: st.metric("Tổng phần mềm", len(df))
        with c2: st.metric("Tổng số bản quyền", total_lic)
        
        # Thống kê rủi ro (Hết hạn < 30 ngày hoặc Low Stock)
        risk_count = len(df[df['sort_priority'] < 3])
        with c3: st.metric("⚠️ Cần xử lý ngay", risk_count, delta_color="inverse")
        
        usage_rate = (df['used_quantity'].sum() / total_lic * 100) if total_lic > 0 else 0
        with c4: st.metric("Tỷ lệ sử dụng", f"{usage_rate:.1f}%")

    # --- 5. BẢNG DỮ LIỆU CHI TIẾT (PRO DISPLAY) ---
    if not df.empty:
        st.markdown("### 📋 Danh sách bản quyền (Sắp xếp theo mức độ ưu tiên)")
        
        # Hiển thị bảng với Column Config chuyên sâu
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
                "expiry_date": st.column_config.DateColumn("Hết hạn", format="DD/MM/YYYY"),
                "Tình trạng": st.column_config.TextColumn("🔍 Đánh giá hệ thống")
            }
        )

    # --- 6. KHU VỰC QUẢN TRỊ ---
    with st.expander("＋ Thêm/Cập nhật bản quyền"):
        # (Giữ nguyên form nhập liệu như cũ của bạn nhưng đảm bảo date_input mặc định là today + 1 year)
        with st.form("add_lic_enterprise_v2", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Tên phần mềm")
            provider = col2.text_input("Nhà cung cấp")
            c1, c2, c3 = st.columns(3)
            total = c1.number_input("Tổng số lượng", min_value=1)
            threshold = c2.number_input("Ngưỡng báo động", value=5)
            expiry = c3.date_input("Ngày hết hạn", value=datetime.now().date().replace(year=datetime.now().year + 1))
            
            if st.form_submit_button("Lưu dữ liệu"):
                if name:
                    supabase.table("licenses").upsert({
                        "name": name.strip(), "total_quantity": total,
                        "expiry_date": str(expiry), "provider": provider,
                        "alert_threshold": threshold
                    }, on_conflict="name").execute()
                    st.success(f"Đã cập nhật {name}")
                    st.rerun()

    # --- 7. KHU VỰC XÓA (COMPACT) ---
    if not df.empty:
        with st.expander("🗑️ Gỡ bỏ phần mềm khỏi hệ thống"):
            del_target = st.selectbox("Chọn phần mềm", ["-- Chọn --"] + df['name'].tolist())
            if st.button("Xác nhận xóa vĩnh viễn", type="primary"):
                if del_target != "-- Chọn --":
                    supabase.table("licenses").delete().eq("name", del_target).execute()
                    st.rerun()
