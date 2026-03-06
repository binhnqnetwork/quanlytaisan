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
with tab1:
    st.header("Danh sách thiết bị theo địa điểm")
    locations = ["Nhà máy Long An", "Chi nhánh Thành phố", "Đà Nẵng", "Miền Bắc", "Polypack"]
    loc_filter = st.selectbox("Chọn địa điểm", locations)
    
    # Sửa query: Đảm bảo tên bảng và cột đúng như SQL
    try:
        # Nếu bạn chưa muốn JOIN phức tạp, hãy lấy đơn giản trước để test:
        res = supabase.table("assets").select("*").eq("location", loc_filter).execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info(f"Chưa có thiết bị nào tại {loc_filter}")
            
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
