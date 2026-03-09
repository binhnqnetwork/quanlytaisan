import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. PHONG CÁCH THIẾT KẾ LUXURY (APPLE-STYLE) ---
    st.markdown("""
        <style>
        .stApp { background-color: #f5f5f7; }
        .main-header { font-size: 2.2rem; font-weight: 800; color: #1d1d1f; letter-spacing: -1px; margin-bottom: 25px; }
        .apple-card {
            background: #ffffff; border-radius: 20px; padding: 25px;
            border: 1px solid rgba(0,0,0,0.05); box-shadow: 0 10px 30px rgba(0,0,0,0.04);
            margin-bottom: 20px; transition: all 0.3s ease;
        }
        .apple-card:hover { transform: translateY(-2px); box-shadow: 0 15px 35px rgba(0,0,0,0.07); }
        .stat-label { color: #86868b; font-size: 0.9rem; font-weight: 500; }
        .stat-value { font-size: 1.8rem; font-weight: 700; color: #1d1d1f; }
        .badge { padding: 5px 14px; border-radius: 12px; font-size: 11px; font-weight: 700; }
        .badge-blue { background: #0071e3; color: white; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-header">📦 Quản trị Tài sản Doanh nghiệp</div>', unsafe_allow_html=True)

    # --- 2. HỆ THỐNG KPI DỰA TRÊN THỜI GIAN THỰC ---
    try:
        with st.spinner("Đang đồng bộ dữ liệu..."):
            res_total = supabase.table("assets").select("id", count="exact").execute()
            res_stock = supabase.table("assets").select("id", count="exact").eq("status", "Trong kho").execute()
            res_deployed = supabase.table("assets").select("id", count="exact").eq("status", "Đang sử dụng").execute()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="apple-card"><div class="stat-label">Tổng thiết bị</div><div class="stat-value">{res_total.count or 0}</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="apple-card"><div class="stat-label">Sẵn sàng cấp</div><div class="stat-value" style="color:#28a745;">{res_stock.count or 0}</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="apple-card"><div class="stat-label">Đang vận hành</div><div class="stat-value" style="color:#0071e3;">{res_deployed.count or 0}</div></div>', unsafe_allow_html=True)
    except:
        st.error("Lỗi kết nối cơ sở dữ liệu.")

    # --- 3. NHẬP KHO THÔNG MINH (FIX TRIỆT ĐỂ LỖI 23514) ---
    with st.expander("📥 Nhập thiết bị mới (Dành cho Admin)", expanded=False):
        # Truy vấn trực tiếp các types hợp lệ từ DB hoặc dùng mapping an toàn
        # Constraint của bạn yêu cầu: LT, PC, MN, SV, OT
        type_options = {"Laptop": "LT", "Desktop PC": "PC", "Monitor": "MN", "Server": "SV", "Khác": "OT"}
        
        with st.form("pro_add_asset", clear_on_submit=True):
            col_a, col_b, col_c = st.columns([1,1,2])
            tag = col_a.text_input("Mã định danh (Asset Tag)", placeholder="VD: PC001")
            label = col_b.selectbox("Loại thiết bị", list(type_options.keys()))
            specs = col_c.text_input("Cấu hình tóm tắt", placeholder="M3 Chip, 16GB RAM...")
            
            if st.form_submit_button("🔥 Xác nhận nhập kho"):
                if tag:
                    # Gửi mã viết tắt (LT, PC...) để thỏa mãn check constraint
                    err = supabase.table("assets").insert({
                        "asset_tag": tag.strip().upper(),
                        "type": type_options[label],
                        "status": "Trong kho",
                        "specs": {"note": specs, "updated_at": str(datetime.now())}
                    }).execute()
                    st.toast(f"Đã thêm {tag} vào kho!", icon="✅")
                    st.rerun()

    # --- 4. TRUNG TÂM QUẢN LÝ NHÂN SỰ & CẤP PHÁT ---
    st.markdown("### 👤 Điều phối Tài sản")
    e_code = st.text_input("Nhập Mã nhân viên", placeholder="VD: 10438").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.markdown(f"""
                <div class="apple-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span class="badge badge-blue">NHÂN VIÊN CHÍNH THỨC</span>
                            <h2 style="margin: 8px 0;">{staff['full_name']}</h2>
                            <p style="color: #86868b; margin: 0;">🏢 {staff.get('branch')} — 📂 {staff.get('department')}</p>
                        </div>
                        <div style="text-align: right;">
                            <code style="background: #f5f5f7; padding: 5px 10px; border-radius: 5px;">ID: {e_code}</code>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            tab_assign, tab_holding = st.tabs(["📤 Bàn giao mới", "💻 Thiết bị đang giữ"])
            
            with tab_assign:
                avail = supabase.table("assets").select("*").eq("status", "Trong kho").execute()
                if avail.data:
                    with st.form("pro_assign"):
                        asset_map = {f"[{a['type']}] {a['asset_tag']}": a for a in avail.data}
                        selected = st.selectbox("Chọn thiết bị sẵn có", list(asset_map.keys()))
                        if st.form_submit_button("Cấp phát thiết bị"):
                            target = asset_map[selected]
                            supabase.table("assets").update({
                                "assigned_to_code": e_code, "status": "Đang sử dụng"
                            }).eq("id", target['id']).execute()
                            st.success(f"Đã bàn giao {target['asset_tag']} cho {staff['full_name']}")
                            st.rerun()
                else:
                    st.info("Kho hiện tại không còn thiết bị trống.")

            with tab_holding:
                my_assets = supabase.table("assets").select("*").eq("assigned_to_code", e_code).execute()
                if my_assets.data:
                    for a in my_assets.data:
                        c_a, c_b = st.columns([3, 1])
                        c_a.write(f"**{a['asset_tag']}** ({a['type']})")
                        if c_b.button("Thu hồi", key=f"rec_{a['id']}", use_container_width=True):
                            supabase.table("assets").update({
                                "assigned_to_code": None, "status": "Trong kho"
                            }).eq("id", a['id']).execute()
                            st.rerun()
                else:
                    st.caption("Không có thiết bị nào được gán cho nhân sự này.")

        else:
            # TỰ ĐỘNG MỞ FORM ĐĂNG KÝ NẾU CHƯA CÓ NHÂN VIÊN
            st.warning(f"Mã {e_code} chưa có trong hệ thống.")
            with st.expander("🆕 Đăng ký hồ sơ nhân sự mới", expanded=True):
                with st.form("pro_new_staff"):
                    name = st.text_input("Họ và Tên")
                    c1, c2 = st.columns(2)
                    
                    # Phòng ban & Chi nhánh theo chuẩn yêu cầu
                    dept_list = ["Nhân viên VP", "Kỹ thuật", "Kế toán", "Kinh doanh", "Sản xuất"]
                    dept_input = c1.selectbox("Phòng ban", dept_list + ["Khác (Nhập tay)"])
                    final_dept = c1.text_input("Nhập tên phòng ban") if dept_input == "Khác (Nhập tay)" else dept_input
                    
                    branch_list = ["Polypack", "Nhà máy LA", "Chi nhánh TPHCM", "Đà Nẵng", "Miền Bắc"]
                    final_branch = c2.selectbox("Chi nhánh công tác", branch_list)
                    
                    if st.form_submit_button("✅ Khởi tạo hồ sơ"):
                        if name and final_dept:
                            supabase.table("staff").insert({
                                "employee_code": e_code, "full_name": name,
                                "department": final_dept, "branch": final_branch
                            }).execute()
                            st.success("Hồ sơ đã được lưu!")
                            st.rerun()

    # --- 5. LOG VẬN HÀNH TOÀN DIỆN ---
    st.markdown("---")
    st.markdown("### 🛠️ Nhật ký hệ thống")
    logs = supabase.table("maintenance_log").select("*, assets(asset_tag)").order("performed_at", desc=True).limit(5).execute()
    if logs.data:
        for l in logs.data:
            st.caption(f"🕒 {l['performed_at']} | **{l['assets']['asset_tag']}**: {l['action_type']}")
