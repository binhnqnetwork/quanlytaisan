import streamlit as st

def login_page(supabase):
    """
    Giao diện đăng nhập chuẩn Enterprise tích hợp Supabase Auth
    """
    # --- 1. CSS CUSTOM CHO TRANG LOGIN ---
    st.markdown("""
        <style>
        /* Ẩn header và menu mặc định của Streamlit khi chưa đăng nhập */
        header {visibility: hidden;}
        
        .login-wrapper {
            max-width: 420px;
            margin: 80px auto;
            padding: 40px;
            background: #ffffff;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.08);
            border: 1px solid #e1e1e1;
        }
        
        .login-title {
            color: #1d1d1f;
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 8px;
            text-align: center;
        }
        
        .login-subtitle {
            color: #86868b;
            font-size: 14px;
            margin-bottom: 32px;
            text-align: center;
        }

        /* Tùy chỉnh nút bấm của Streamlit trong form login */
        .stButton > button {
            width: 100%;
            background-color: #0071e3 !important;
            color: white !important;
            border-radius: 12px !important;
            height: 48px !important;
            font-weight: 600 !important;
            border: none !important;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #0077ed !important;
            box-shadow: 0 4px 12px rgba(0,113,227,0.3);
        }

        /* Hiệu ứng focus cho input */
        .stTextInput input {
            border-radius: 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. GIAO DIỆN LOGIN ---
    # Sử dụng cột để căn giữa form trên màn hình wide
    _, col, _ = st.columns([1, 1.5, 1])

    with col:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        
        # Logo/Icon hệ thống
        st.markdown("<h1 style='text-align: center; font-size: 50px; margin-bottom: 0;'>🚀</h1>", unsafe_allow_html=True)
        st.markdown('<p class="login-title">Asset Admin Center</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Vui lòng đăng nhập để tiếp tục quản trị hệ thống</p>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email công ty", placeholder="admin@company.com")
            password = st.text_input("Mật khẩu", type="password", placeholder="••••••••")
            
            # Nút submit
            submitted = st.form_submit_button("Đăng nhập hệ thống")

            if submitted:
                if not email or not password:
                    st.error("Vui lòng nhập đầy đủ Email và Mật khẩu.")
                else:
                    try:
                        # Gọi API xác thực của Supabase
                        auth_response = supabase.auth.sign_in_with_password({
                            "email": email, 
                            "password": password
                        })
                        
                        # Nếu thành công, lưu vào session_state
                        if auth_response.user:
                            st.session_state.authenticated = True
                            st.session_state.user_email = auth_response.user.email
                            st.session_state.user_id = auth_response.user.id
                            
                            st.toast("Đăng nhập thành công!", icon="✅")
                            st.rerun()
                            
                    except Exception as e:
                        # Xử lý lỗi đăng nhập (sai pass, email không tồn tại...)
                        error_msg = str(e)
                        if "Invalid login credentials" in error_msg:
                            st.error("Thông tin đăng nhập không chính xác.")
                        else:
                            st.error(f"Lỗi xác thực: {error_msg}")

        st.markdown('<p style="text-align: center; font-size: 12px; color: #bfbfbf; margin-top: 20px;">Secure Enterprise Authentication Service v2.0</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    """
    Hàm xử lý đăng xuất nhanh
    """
    st.session_state.authenticated = False
    st.session_state.user_email = None
    st.rerun()
