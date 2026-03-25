import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_licenses(supabase):
    # --- 1. CSS & HEADER ---
    st.markdown("""
        <style>
        .main-header { font-weight: 700; color: #1d1d1f; margin-bottom: 20px; }
        .apple-card {
            background: #ffffff; border-radius: 16px; padding: 20px;
            border: 1px solid #d2d2d7; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. TRUY VẤN DỮ LIỆU GỐC
    res = supabase.table("licenses").select("*").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- 3. KHU VỰC TIÊU ĐỀ & XUẤT BÁO CÁO (LUÔN HIỂN THỊ) ---
    col_t, col_e = st.columns([3, 1])
    with col_t:
        st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)
    
    with col_e:
        if not df.empty:
            # Chức năng Tải báo cáo - Xuất hiện góc trên bên phải
            csv = df.to_csv(index=False).encode('utf-16')
            st.download_button(
                label="📥 Tải báo cáo Excel",
                data=csv,
                file_name=f"Asset_Report_{date.today()}.csv",
                mime='text/csv',
                use_container_width=True
            )

    # --- 4. LOGIC XỬ LÝ DỮ LIỆU & KPI ---
    if not df.empty:
        # [Các bước tính toán sort_priority, days_to_expiry, Tình trạng giống như bài trước]
        # ... (Phần code xử lý df ở đây) ...

        # Hiển thị KPI Stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng phần mềm", len(df)) #
        c2.metric("Tổng số bản quyền", df['total_quantity'].sum()) #[cite: 7]
        c3.metric("⚠️ Cần xử lý", len(df[df['total_quantity'] - df['used_quantity'] <= 5]))
        c4.metric("Tỷ lệ sử dụng", f"{(df['used_quantity'].sum()/df['total_quantity'].sum()*100):.1f}%") #[cite: 7]

        # Hiển thị Bảng danh sách[cite: 7]
        st.dataframe(df[['name', 'total_quantity', 'used_quantity', 'expiry_date']], use_container_width=True)

    # --- 5. CHỨC NĂNG THU HỒI (PHẢI NẰM NGOÀI CÁC EXPANDER KHÁC) ---
    st.markdown("---")
    with st.expander("🔄 THU HỒI BẢN QUYỀN (Harvesting Mode)", expanded=False):
        st.markdown("Chọn thiết bị để thu hồi License về kho.")
        # Logic truy vấn assets và form thu hồi tôi đã gửi ở trên
        # Đảm bảo phần này nằm tách biệt để dễ nhìn thấy
        st.info("Chức năng này giúp tái sử dụng License từ máy hỏng hoặc nhân viên nghỉ việc.")
        # [Chèn đoạn code Form Thu Hồi ở đây...]

    # --- 6. CÁC TIỆN ÍCH KHÁC (EXPANDERS) ---
    with st.expander("＋ Thêm/Cập nhật bản quyền"): #[cite: 7]
        pass # Code form thêm mới

    with st.expander("🗑️ Gỡ bỏ phần mềm khỏi hệ thống"): #[cite: 7]
        pass # Code xóa
