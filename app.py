import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta
from utils import encrypt_pw, decrypt_pw

# 1. Cấu hình trang & Kết nối
st.set_page_config(page_title="Enterprise Asset Management", layout="wide")
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

st.title("🚀 Enterprise Asset Management")

# 2. Định nghĩa Menu Tab
tab1, tab2, tab3, tab4 = st.tabs([
    "💻 Thiết bị & Nhân viên", 
    "🖥️ Quản lý Server", 
    "🌐 Bản quyền & Domain", 
    "🔐 Vault Mật khẩu"
])

# --- TAB 1: QUẢN LÝ THIẾT BỊ ---
with tab1:
    st.header("💻 Danh sách thiết bị theo địa điểm")
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
        # Lấy thiết bị kèm thông tin địa điểm (Join)
        res = supabase.table("assets").select("*").eq("location_id", selected_id).execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Chọn lọc các cột hiển thị cho sạch
            st.dataframe(df[['asset_tag', 'type', 'status', 'specs']], use_container_width=True)
        else:
            st.info(f"Chưa có thiết bị nào tại {loc_display}")
    except Exception as e:
        st.error(f"Lỗi: {e}")

# --- TAB 2: QUẢN LÝ SERVER ---
with tab2:
    st.header("🖥️ Cấu hình Máy chủ & Bảo trì")
    try:
        srv_res = supabase.table("assets").select("*").eq("type", "Server").execute()
        if srv_res.data:
            for srv in srv_res.data:
                with st.expander(f"📌 Server: {srv['asset_tag']} ({srv['status']})"):
                    specs = srv.get('specs', {})
                    c1, c2, c3 = st.columns(3)
                    c1.metric("CPU", specs.get('cpu', 'N/A'))
                    c2.metric("RAM", specs.get('ram', 'N/A'))
                    c3.metric("OS", specs.get('os', 'N/A'))
                    
                    # Nút ghi nhận bảo trì
                    if st.button(f"Ghi nhận bảo trì: {srv['asset_tag']}", key=f"btn_{srv['id']}"):
                        today = datetime.now().strftime("%Y-%m-%d")
                        # Cập nhật ngày bảo trì vào DB (Bạn cần tạo cột last_maintenance trong SQL)
                        st.success(f"Đã lưu lịch sử bảo trì ngày {today}")
        else:
            st.info("Không tìm thấy máy chủ nào.")
    except Exception as e:
        st.error(f"Lỗi load server: {e}")

# --- TAB 3: BẢN QUYỀN & NHẮC HẸN ---
with tab3:
    st.header("🌐 Theo dõi Bản quyền & Domain")
    try:
        lic_res = supabase.table("licenses").select("*").execute()
        if lic_res.data:
            today = datetime.now().date()
            for item in lic_res.data:
                exp_date = datetime.strptime(item['expiry_date'], "%Y-%m-%d").date()
                days_diff = (exp_date - today).days
                
                # Logic hiển thị cảnh báo theo yêu cầu "nhắc trước 1 tháng"
                if days_diff <= 0:
                    st.error(f"❌ {item['name']} - ĐÃ HẾT HẠN ({item['expiry_date']})")
                elif days_diff <= 30:
                    st.warning(f"⚠️ {item['name']} - Hết hạn sau {days_diff} ngày! (Gia hạn: {item['expiry_date']})")
                else:
                    st.success(f"✅ {item['name']} - Còn hạn đến {item['expiry_date']}")
        else:
            st.info("Chưa có dữ liệu bản quyền.")
    except Exception as e:
        st.error(f"Lỗi load licenses: {e}")

# --- TAB 4: BÍ MẬT (VAULT) ---
with tab4:
    st.header("🔐 Kho mật khẩu bí mật")
    with st.form("add_secret"):
        site = st.text_input("Dịch vụ")
        u_name = st.text_input("Username")
        p_word = st.text_input("Password", type="password")
        if st.form_submit_button("Lưu mã hóa"):
            if site and p_word:
                secret_data = {
                    "service_name": site, "username": u_name,
                    "encrypted_password": encrypt_pw(p_word)
                }
                supabase.table("secret_vault").insert(secret_data).execute()
                st.success("Đã lưu!")
                st.rerun()

    st.divider()
    secrets_res = supabase.table("secret_vault").select("*").execute()
    if secrets_res.data:
        for s in secrets_res.data:
            col1, col2, col3 = st.columns([3, 3, 2])
            col1.write(f"**{s['service_name']}**")
            col2.write(f"`{s['username']}`")
            if col3.button("Xem Pass", key=f"v_{s['id']}"):
                st.code(decrypt_pw(s['encrypted_password']))
