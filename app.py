import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from utils import encrypt_pw, decrypt_pw

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

-- Thêm nhân viên mẫu
INSERT INTO staff (full_name, employee_code, location) 
VALUES 
('Nguyễn Văn A', 'NV001', 'Nhà máy Long An'),
('Trần Thị B', 'NV002', 'Chi nhánh Thành phố');

-- Thêm thiết bị mẫu (Chú ý cột type và specs)
INSERT INTO assets (asset_tag, type, location_id, status, specs)
VALUES 
('SRV-001', 'Server', 2, 'Active', '{"cpu": "Xeon E-2300", "ram": "64GB", "os": "Ubuntu 22.04"}'),
('SRV-002', 'Server', 1, 'Active', '{"cpu": "Core i9", "ram": "128GB", "os": "Windows Server 2022"}'),
('LAP-001', 'Laptop', 1, 'Active', '{"cpu": "M2", "ram": "16GB", "os": "macOS"}');

-- Thêm bản quyền mẫu để test Tab 3
INSERT INTO licenses (name, expiry_date, provider)
VALUES 
('Office 365 Enterprise', '2026-04-01', 'Microsoft'),
('Domain polypack.com.vn', '2026-03-25', 'PA Vietnam');
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
    st.header("🔐 Kho mật khẩu bí mật")
    
    # Form thêm mới
    with st.form("add_secret"):
        site = st.text_input("Dịch vụ (Ví dụ: Gmail Admin)")
        user = st.text_input("Tên đăng nhập")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.form_submit_button("Lưu mã hóa"):
            secret_data = {
                "service_name": site,
                "username": user,
                "encrypted_password": encrypt_pw(pwd)
            }
            supabase.table("secret_vault").insert(secret_data).execute()
            st.success("Đã lưu mật khẩu an toàn!")

    # Hiển thị danh sách
    st.divider()
    secrets_res = supabase.table("secret_vault").select("*").execute()
    if secrets_res.data:
        for s in secrets_res.data:
            col1, col2, col3 = st.columns([3, 3, 2])
            col1.write(f"**{s['service_name']}**")
            col2.write(f"`{s['username']}`")
            if col3.button("Xem Pass", key=f"view_{s['id']}"):
                st.code(decrypt_pw(s['encrypted_password']))
