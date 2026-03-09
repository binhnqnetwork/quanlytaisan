import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def get_maintenance_config(asset_type):
    """Cấu hình số tháng bảo trì định kỳ dựa trên loại thiết bị"""
    configs = {
        'server': 3, 'laptop': 6, 'pc': 6, 
        'network': 12, 'monitor': 24, 'other': 12
    }
    return configs.get(asset_type, 6)

def render_inventory(supabase):
    # --- APPLE UI/UX CUSTOM CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        
        /* Cấu trúc nền và font */
        .stApp { background-color: #f5f5f7; font-family: 'Inter', sans-serif; }
        
        /* Header style */
        .main-header { 
            font-size: 34px; font-weight: 600; color: #1d1d1f; 
            letter-spacing: -0.8px; margin-bottom: 5px; 
        }
        .sub-header { color: #86868b; font-size: 17px; margin-bottom: 30px; }

        /* Card Design */
        .apple-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 18px;
            padding: 24px;
            border: 1px solid rgba(210, 210, 215, 0.5);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
        }

        /* Badge Status */
        .badge {
            padding: 4px 10px; border-radius: 6px; font-size: 12px; 
            font-weight: 600; text-transform: uppercase;
        }
        .badge-blue { background: #e8f2ff; color: #0066cc; }
        .badge-orange { background: #fff4e5; color: #b76e00; }
        
        /* Input styling */
        .stTextInput input { border-radius: 10px !important; }
        .stButton button { 
            border-radius: 10px !important; background-color: #0071e3 !important; 
            color: white !important; font-weight: 500 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    st.markdown('<h1 class="main-header">Inventory System</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Quản lý cấp phát & Theo dõi vòng đời thiết bị chuyên nghiệp</p>', unsafe_allow_html=True)

    # --- SECTION 1: NHẬP KHO THÔNG MINH (AUTO-VALIDATOR) ---
    with st.expander("📥 Nhập thiết bị mới vào kho", expanded=False):
        with st.form("apple_add_stock", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 2, 3])
            new_tag = c1.text_input("Asset Tag", placeholder="VD: LT-2026-001")
            
            type_map = {
                "MacBook / Laptop": "laptop",
                "iMac / PC Desktop": "pc",
                "Display / Monitor": "monitor",
                "Printer": "printer",
                "Network Device": "network",
                "Server": "server",
                "Other": "other"
            }
            selected_label = c2.selectbox("Phân loại", list(type_map.keys()))
            new_specs = c3.text_input("Cấu hình chi tiết", placeholder="M3 Max, 32GB, 1TB SSD")
            
            if st.form_submit_button("Lưu vào kho hệ thống"):
                if new_tag:
                    db_type = type_map[selected_label]
                    m_months = get_maintenance_config(db_type)
                    recommend = f"💡 Bảo trì định kỳ mỗi {m_months} tháng."
                    
                    try:
                        supabase.table("assets").insert({
                            "asset_tag": new_tag.strip().upper(),
                            "type": db_type,
                            "status": "Trong kho",
                            "specs": {"note": new_specs},
                            "recommendations": recommend,
                            "assigned_to_code": None
                        }).execute()
                        st.toast(f"Đã nhập kho {new_tag} thành công!", icon="✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    # --- SECTION 2: QUẢN LÝ NHÂN SỰ ---
    st.markdown("### 👤 Tra cứu nhân sự")
    e_code = st.text_input("Mã nhân viên", placeholder="Nhập ID để cấp phát hoặc thu hồi...", label_visibility="collapsed").strip().upper()

    if e_code:
        # Lấy thông tin Staff & Assets
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            # Card nhân viên
            st.markdown(f"""
                <div class="apple-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span class="badge badge-blue">{staff['employee_code']}</span>
                            <h2 style="margin: 10px 0 0 0; font-size: 24px;">{staff['full_name']}</h2>
                            <p style="color: #86868b; margin: 0;">{staff['department']} • {staff['branch']}</p>
                        </div>
                        <div style="text-align: right;">
                            <p style="font-size: 12px; color: #86868b; margin: 0;">TRẠNG THÁI</p>
                            <span style="color: #34c759; font-weight: 600;">● Đang làm việc</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            col_left, col_right = st.columns([1, 1], gap="large")
            
            # --- CẤP PHÁT ---
            with col_left:
                st.markdown("#### 📦 Bàn giao thiết bị")
                available = supabase.table("assets").select("*").eq("status", "Trong kho").neq("type", "server").execute()
                
                if available.data:
                    with st.form("assign_form_apple"):
                        # Hiển thị Tag kèm thông tin khuyến nghị bảo trì
                        asset_options = {f"{a['asset_tag']} ({a['type']})": a for a in available.data}
                        selected_display = st.selectbox("Chọn từ kho", asset_options.keys())
                        chosen_asset = asset_options[selected_display]
                        
                        # Cảnh báo bảo trì nếu có
                        if chosen_asset.get('recommendations'):
                            st.caption(f"{chosen_asset['recommendations']}")
                            
                        date_assign = st.date_input("Ngày gán")
                        
                        if st.form_submit_button("Xác nhận bàn giao"):
                            supabase.table("assets").update({
                                "assigned_to_code": e_code,
                                "status": "Đang sử dụng",
                                "purchase_date": str(date_assign)
                            }).eq("asset_tag", chosen_asset['asset_tag']).execute()
                            st.rerun()
                else:
                    st.info("Kho hiện không có thiết bị sẵn sàng.")

            # --- DANH SÁCH ĐANG GIỮ ---
            with col_right:
                st.markdown("#### 🖥️ Thiết bị đang sử dụng")
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                
                if my_assets.data:
                    for a in my_assets.data:
                        with st.container(border=True):
                            c_info, c_btn = st.columns([3, 1])
                            c_info.markdown(f"**{a['asset_tag']}**")
                            c_info.caption(f"{a['type'].upper()} • Gán: {a.get('purchase_date', 'N/A')}")
                            if c_btn.button("Thu hồi", key=f"ret_{a['asset_tag']}"):
                                supabase.table("assets").update({
                                    "assigned_to_code": None, "status": "Trong kho"
                                }).eq("asset_tag", a['asset_tag']).execute()
                                st.rerun()
                else:
                    st.write("*(Chưa giữ thiết bị nào)*")

            # --- NHẬT KÝ BẢO TRÌ ---
            st.markdown("---")
            st.markdown("### 🛠️ Nhật ký bảo trì & Sửa chữa")
            asset_dict = {a['asset_tag']: a['id'] for a in my_assets.data}
            
            if asset_dict:
                with st.expander("Ghi nhật ký mới"):
                    with st.form("apple_maint_form"):
                        sel_tag = st.selectbox("Thiết bị", list(asset_dict.keys()))
                        m_type = st.selectbox("Hình thức", ["Bảo trì định kỳ", "Sửa chữa phần cứng", "Nâng cấp", "Cài đặt phần mềm"])
                        m_desc = st.text_area("Chi tiết xử lý", placeholder="VD: Thay keo tản nhiệt, vệ sinh quạt...")
                        if st.form_submit_button("Lưu lịch sử"):
                            today = str(datetime.now().date())
                            supabase.table("maintenance_log").insert({
                                "asset_id": asset_dict[sel_tag],
                                "action_type": m_type,
                                "description": m_desc,
                                "performed_at": today
                            }).execute()
                            # Update ngày bảo trì cuối
                            supabase.table("assets").update({"last_maintenance": today}).eq("id", asset_dict[sel_tag]).execute()
                            st.success("Đã cập nhật lịch sử bảo trì!")
                            st.rerun()
                
                # Table lịch sử
                logs = supabase.table("maintenance_log").select("*").in_("asset_id", list(asset_dict.values())).order("performed_at", desc=True).execute()
                if logs.data:
                    df_logs = pd.DataFrame(logs.data)[['performed_at', 'action_type', 'description']]
                    st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.warning("Mã nhân viên không tồn tại trong hệ thống.")
