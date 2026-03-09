import streamlit as st
import pandas as pd
from datetime import datetime
import io

def render_inventory(supabase):
    # --- 1. CẤU HÌNH HỆ THỐNG & MAPPING (FIX LỖI 23514) ---
    # Ánh xạ nhãn hiển thị sang mã máy chuẩn của Database
    type_mapping = {
        "Laptop": "LT", "Desktop PC": "PC", "Monitor": "MN", "Server": "SV", "Khác": "OT"
    }
    # Mapping hậu tố chi nhánh cho Asset Tag
    branch_map = {
        "Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", 
        "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"
    }

    # --- 2. GIAO DIỆN APPLE-INSPIRED ---
    st.markdown("""
        <style>
        .stApp { background-color: #f8f9fa; }
        .stat-card {
            background: white; padding: 20px; border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center;
        }
        .stat-val { font-size: 24px; font-weight: 700; color: #0066cc; }
        .badge-status { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
        </style>
    """, unsafe_allow_html=True)

    st.title("📦 Quản trị Tài sản Doanh nghiệp")

    # --- 3. DASHBOARD TỔNG QUAN ---
    res_all = supabase.table("assets").select("status", count="exact").execute()
    total_assets = res_all.count if res_all.count else 0
    in_stock = len([x for x in res_all.data if x['status'] == 'Trong kho'])
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-card">Tổng thiết bị<br><span class="stat-val">{total_assets}</span></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-card">Sẵn sàng cấp<br><span class="stat-val" style="color:#28a745;">{in_stock}</span></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="stat-card">Đang vận hành<br><span class="stat-val" style="color:#fd7e14;">{total_assets - in_stock}</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- 4. NHẬP KHO THÔNG MINH (FIX LỖI CHECK CONSTRAINT) ---
    with st.expander("📥 Nhập thiết bị mới (Hệ thống tự động tạo mã)", expanded=False):
        with st.form("inventory_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            num_id = col1.text_input("Số seri/mã máy", placeholder="VD: 0001")
            area = col2.selectbox("Khu vực quản lý", list(branch_map.keys()))
            category = col3.selectbox("Loại thiết bị", list(type_mapping.keys()))
            
            # Logic: PC0001-MB (Tag tự do nhưng Type phải chuẩn mã ngắn)
            tag_preview = f"{type_mapping[category]}{num_id.strip().upper()}-{branch_map[area]}"
            st.caption(f"Mã Asset Tag dự kiến: **{tag_preview}**")
            
            specs = st.text_area("Thông số kỹ thuật", placeholder="Chip, RAM, SSD, năm sản xuất...")

            if st.form_submit_button("Xác nhận Nhập kho"):
                if num_id:
                    try:
                        # FIX LỖI 23514: Gửi type_mapping[category] (VD: 'PC') thay vì 'Desktop PC'
                        supabase.table("assets").insert({
                            "asset_tag": tag_preview,
                            "type": type_mapping[category], 
                            "status": "Trong kho",
                            "specs": {"details": specs, "input_date": str(datetime.now().date())}
                        }).execute()
                        st.success(f"Đã nhập kho thành công thiết bị {tag_preview}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi Database: {e}")

    # --- 5. QUẢN LÝ DANH SÁCH & XUẤT DỮ LIỆU ---
    st.subheader("🔍 Danh mục Tài sản")
    vung_filter = st.segmented_control("Lọc theo chi nhánh:", ["Tất cả"] + list(branch_map.keys()), default="Tất cả")
    
    query = supabase.table("assets").select("*")
    if vung_filter != "Tất cả":
        query = query.ilike("asset_tag", f"%-{branch_map[vung_filter]}")
    
    assets_data = query.execute()
    
    if assets_data.data:
        df = pd.DataFrame(assets_data.data)
        
        # Tạo file Excel để tải về (Sự chuyên nghiệp cho báo cáo)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='TaiSan')
        
        st.download_button(
            label="📊 Xuất danh sách Excel",
            data=buffer.getvalue(),
            file_name=f"TaiSan_{vung_filter}_{datetime.now().strftime('%d%m%y')}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        # Hiển thị bảng dữ liệu
        st.dataframe(df[['asset_tag', 'type', 'status', 'assigned_to_code', 'purchase_date']], 
                     use_container_width=True)
    else:
        st.info("Không có dữ liệu phù hợp với bộ lọc.")

    # --- 6. CẤP PHÁT CHO NHÂN VIÊN ---
    st.markdown("---")
    st.subheader("👤 Cấp phát & Bàn giao")
    e_code = st.text_input("Nhập Mã nhân viên", placeholder="VD: 10438").strip().upper()

    if e_code:
        res_staff = supabase.table("staff").select("*").eq("employee_code", e_code).execute()
        
        if res_staff.data:
            staff = res_staff.data[0]
            st.success(f"Nhân viên: **{staff['full_name']}** | {staff['department']} ({staff['branch']})")
            
            # Chọn thiết bị còn trống
            avail = supabase.table("assets").select("id, asset_tag, type").eq("status", "Trong kho").execute()
            if avail.data:
                with st.form("assignment"):
                    target = st.selectbox("Chọn thiết bị bàn giao", 
                                          options=[f"{x['asset_tag']} - {x['type']}" for x in avail.data])
                    asset_id = [x['id'] for x in avail.data if f"{x['asset_tag']} - {x['type']}" == target][0]
                    
                    if st.form_submit_button("Xác nhận Bàn giao"):
                        supabase.table("assets").update({
                            "assigned_to_code": e_code, "status": "Đang sử dụng"
                        }).eq("id", asset_id).execute()
                        st.balloons()
                        st.rerun()
            else:
                st.warning("Kho hiện tại không còn thiết bị trống.")
        else:
            st.error("Mã nhân viên không tồn tại trong hệ thống.")
