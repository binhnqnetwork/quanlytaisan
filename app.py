import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta

# Kết nối Supabase
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title("🚀 Enterprise Asset Management")

tab1, tab2, tab3, tab4 = st.tabs([
    "💻 Thiết bị & Nhân viên", 
    "🖥️ Quản lý Server", 
    "🌐 Bản quyền & Domain", 
    "🔐 Vault Mật khẩu"
])

# --- TAB 1: QUẢN LÝ THIẾT BỊ ---
# --- TAB 1: QUẢN LÝ THIẾT BỊ ---
# --- TAB 1: QUẢN LÝ THIẾT BỊ ---
with tab1:
    st.header("💻 Danh sách thiết bị")
    
    # 1. Định nghĩa danh sách địa điểm khớp với ID trong Database của bạn
    # Giả sử: 1: Long An, 2: TP.HCM, 3: Đà Nẵng...
    location_map = {
        "Nhà máy Long An": 1,
        "Chi nhánh Thành phố": 2,
        "Đà Nẵng": 3,
        "Miền Bắc": 4,
        "Polypack": 5
    }
    
    loc_display = st.selectbox("Chọn địa điểm", list(location_map.keys()))
    selected_id = location_map[loc_display]
    
    try:
        # 2. Query chuẩn: Lấy tất cả cột của assets + lấy full_name từ bảng staff (nếu có FK)
        # Lọc theo cột location_id (đã sửa tên cột theo lỗi bạn gặp)
        res = supabase.table("assets")\
            .select("asset_tag, type, specs, status, location_id")\
            .eq("location_id", selected_id)\
            .execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            # Làm đẹp hiển thị JSON specs nếu cần
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"Chưa có thiết bị nào tại {loc_display} (ID: {selected_id})")
            
    except Exception as e:
        st.error(f"Lỗi truy vấn: {e}")

# --- TAB 3: BẢN QUYỀN & NHẮC HẸN ---
with tab3:
    st.header("Theo dõi bản quyền & Domain")
    
    # Logic nhắc hẹn trước 1 tháng
    today = datetime.now().date()
    warning_period = today + timedelta(days=30)
    
    res = supabase.table("licenses").select("*").execute()
    if res.data:
        df = pd.DataFrame(res.data)
        df['expiry_date'] = pd.to_datetime(df['expiry_date']).dt.date
        
        # Highlight các dòng sắp hết hạn
        def highlight_expiry(row):
            if row['expiry_date'] <= warning_period:
                return ['background-color: #ff4b4b'] * len(row)
            return [''] * len(row)
            
        st.dataframe(df.style.apply(highlight_expiry, axis=1))

# --- TAB 4: BÍ MẬT (VAULT) ---
with tab4:
    st.header("Kho mật khẩu nội bộ")
    with st.expander("➕ Thêm mật khẩu mới"):
        site = st.text_input("Trang web/Dịch vụ")
        u_name = st.text_input("Username")
        p_word = st.text_input("Password", type="password")
        if st.button("Lưu bảo mật"):
            from utils import encrypt_password
            enc_p = encrypt_password(p_word)
            supabase.table("secret_vault").insert({
                "service_name": site, "username": u_name, "encrypted_password": enc_p
            }).execute()
            st.success("Đã mã hóa và lưu trữ!")
