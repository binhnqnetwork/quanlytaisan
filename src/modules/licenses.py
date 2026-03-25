import streamlit as st
import pandas as pd
from datetime import datetime

def render_licenses(supabase):
    # [Giữ nguyên phần Style và Truy vấn dữ liệu từ code trước của bạn...]
    res = supabase.table("licenses").select("*").order("name").execute()
    df = pd.DataFrame(res.data) if res.data else pd.DataFrame()

    # --- A. CHỨC NĂNG XUẤT BÁO CÁO (NEW) ---
    st.markdown('<h1 class="main-header">🌐 Quản lý Bản quyền Enterprise</h1>', unsafe_allow_html=True)
    
    col_title, col_export = st.columns([3, 1])
    with col_export:
        if not df.empty:
            # Tạo file CSV để tải về (Hỗ trợ tiếng Việt với utf-16)
            csv = df.to_csv(index=False).encode('utf-16')
            st.download_button(
                label="📥 Tải báo cáo Excel",
                data=csv,
                file_name=f"Bao_cao_Ban_quyen_{datetime.now().strftime('%d%m%Y')}.csv",
                mime='text/csv',
                use_container_width=True
            )

    # [Giữ nguyên phần KPI Stats và Bảng hiển thị từ code trước...]

    st.markdown("---")
    
    # --- B. CHỨC NĂNG THU HỒI BẢN QUYỀN (CORE UPGRADE) ---
    with st.expander("🔄 Thu hồi bản quyền (Từ máy hỏng / Nhân viên nghỉ)"):
        st.info("Sử dụng chức năng này để thu hồi License về kho khi thiết bị không còn sử dụng.")
        
        # 1. Chọn máy cần thu hồi
        res_assets = supabase.table("assets").select("id, asset_tag, software_list, assigned_to_code").execute()
        # Chỉ lọc những máy đang có cài phần mềm
        assets_with_sw = [a for a in res_assets.data if a.get('software_list') and len(a['software_list']) > 0]
        
        if assets_with_sw:
            with st.form("harvest_license_form"):
                option_map = {f"{a['asset_tag']} (Đang giữ: {len(a['software_list'])} SW)": a for a in assets_with_sw}
                selected_asset_label = st.selectbox("Chọn thiết bị nguồn", list(option_map.keys()))
                asset_data = option_map[selected_asset_label]
                
                # 2. Chọn phần mềm cụ thể muốn thu hồi trên máy đó
                sw_to_remove = st.multiselect("Chọn các phần mềm cần thu hồi về kho", asset_data['software_list'])
                
                if st.form_submit_button("Xác nhận Thu hồi", type="primary"):
                    if sw_to_remove:
                        try:
                            # Cập nhật bảng Assets: Loại bỏ các SW đã chọn
                            new_sw_list = [sw for sw in asset_data['software_list'] if sw not in sw_to_remove]
                            supabase.table("assets").update({"software_list": new_sw_list}).eq("id", asset_data['id']).execute()
                            
                            # Cập nhật bảng Licenses: Cộng lại số lượng khả dụng cho từng phần mềm
                            for sw_name in sw_to_remove:
                                # Lấy dữ liệu license hiện tại
                                lic_data = supabase.table("licenses").select("id, used_quantity").eq("name", sw_name).execute()
                                if lic_data.data:
                                    current_used = lic_data.data[0]['used_quantity'] or 0
                                    new_used = max(0, current_used - 1)
                                    supabase.table("licenses").update({"used_quantity": new_used}).eq("id", lic_data.data[0]['id']).execute()
                            
                            st.success(f"Đã thu hồi thành công {len(sw_to_remove)} bản quyền từ máy {asset_data['asset_tag']}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi khi thu hồi: {e}")
                    else:
                        st.warning("Vui lòng chọn ít nhất một phần mềm để thu hồi.")
        else:
            st.write("Không có thiết bị nào đang gán bản quyền để thu hồi.")

    # [Giữ nguyên phần Thêm mới và Xóa của bạn...]
