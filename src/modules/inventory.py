import streamlit as st
import pandas as pd
from datetime import datetime

def render_inventory(supabase):
    # --- 1. MAPPING CHUẨN XÁC VỚI DATABASE (VIẾT THƯỜNG TOÀN BỘ) ---
    # Chú ý: Giá trị bên phải (pc, laptop, server...) phải giống hệt cột 'type' trong DB của bạn
    type_mapping = {
        "Desktop PC": "pc",
        "Laptop": "laptop",
        "Server": "server",
        "Monitor": "monitor",
        "Khác": "other"
    }
    
    branch_map = {
        "Miền Bắc": "MB", "Chi nhánh TPHCM": "HCM", 
        "Nhà máy LA": "LA", "Polypack": "PP", "Đà Nẵng": "DN"
    }

    st.title("📦 Hệ thống Quản trị Tài sản")

    # --- 2. FORM NHẬP KHO "ZERO ERROR" ---
    with st.expander("📥 Nhập thiết bị mới", expanded=True):
        with st.form("final_fix_form"):
            c1, c2, c3 = st.columns(3)
            
            num_id = c1.text_input("Số máy (VD: 0001)")
            area = c2.selectbox("Chi nhánh", list(branch_map.keys()))
            label = c3.selectbox("Loại thiết bị", list(type_mapping.keys()))
            
            # Tạo Asset Tag theo ý bạn: VD PC0001-MB
            db_type = type_mapping[label]
            full_tag = f"{db_type.upper()}{num_id.strip().upper()}-{branch_map[area]}"
            
            specs = st.text_input("Ghi chú cấu hình")

            if st.form_submit_button("Xác nhận Nhập kho"):
                if num_id:
                    try:
                        # Gửi 'pc', 'laptop'... (viết thường) để khớp với Constraint
                        supabase.table("assets").insert({
                            "asset_tag": full_tag,
                            "type": db_type, # Gửi giá trị đã mapping viết thường
                            "status": "Trong kho",
                            "specs": {"detail": specs},
                            "created_at": datetime.now().isoformat()
                        }).execute()
                        st.success(f"✅ Đã thêm: {full_tag}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi vi phạm Database: {e}")

    # --- 3. HIỂN THỊ DANH SÁCH ---
    st.markdown("### 📋 Danh sách hiện tại")
    res = supabase.table("assets").select("*").order("created_at", desc=True).execute()
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df[['asset_tag', 'type', 'status', 'assigned_to_code', 'purchase_date']], use_container_width=True)
