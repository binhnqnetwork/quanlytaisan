import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - PHIÊN BẢN FIX TRIỆT ĐỂ.
    Cơ chế: Ép khớp dữ liệu tuyệt đối bằng cách loại bỏ mọi ký tự không phải số.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    df_ai_base = pd.DataFrame()
    branch_stats, dept_stats = pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, pd.DataFrame(), branch_stats, dept_stats, pd.DataFrame()

    # -------------------------------------------------
    # 2. CHIẾN THUẬT FIX TRIỆT ĐỂ: ÉP KIỂU SỐ NGUYÊN BẢN
    # -------------------------------------------------
    def force_clean_to_string(series):
        # Bước 1: Ép về string và xóa đuôi .0 của float
        # Bước 2: Regex [^\d] xóa sạch mọi thứ KHÔNG PHẢI LÀ SỐ (khoảng trắng, dấu cách ẩn, chữ...)
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.replace(r'[^\d]', '', regex=True) 
            .replace('', np.nan)
        )

    df_assets = df_assets.copy()
    df_assets['assigned_to_code_clean'] = force_clean_to_string(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. MERGE VỚI BẢNG STAFF (ƯU TIÊN HIỂN THỊ TÊN)
    # -------------------------------------------------
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['employee_code_clean'] = force_clean_to_string(df_staff['employee_code'])
        
        # Chỉ lấy các cột cần thiết để tránh trùng lặp
        staff_subset = df_staff[['employee_code_clean', 'full_name', 'department', 'branch']].drop_duplicates('employee_code_clean')
        
        df_ai_base = pd.merge(
            df_assets, 
            staff_subset, 
            left_on='assigned_to_code_clean', 
            right_on='employee_code_clean', 
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()

    # -------------------------------------------------
    # 4. LOGIC GÁN NHÃN THEO YÊU CẦU CỦA BẠN
    # -------------------------------------------------
    # Đảm bảo các cột hiển thị tồn tại
    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = None

    # Điều kiện 1: Tài sản chưa được cấp phát (Mã trống)
    mask_stock = df_ai_base['assigned_to_code_clean'].isna()
    
    # Điều kiện 2: Có mã nhưng không tìm thấy Tên trong bảng Staff (Lệch dữ liệu)
    mask_mismatch = df_ai_base['assigned_to_code_clean'].notna() & df_ai_base['full_name'].isna()

    # Thực hiện gán nhãn cho Kho tổng
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # Thực hiện gán nhãn cho trường hợp Lỗi (để bạn đi sửa data)
    df_ai_base.loc[mask_mismatch, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 5. CÁC PHẦN TÍNH TOÁN KHÁC (Giữ nguyên)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    # Phân cấp rủi ro đơn giản
    df_ai_base["risk_score"] = np.minimum(df_ai_base["m_count"] / 3, 1.0) # Ví dụ
    df_ai_base["risk_level"] = np.where(df_ai_base["risk_score"] > 0.6, "🔴 Nguy cấp", "🟢 Thấp")

    # Groupby để vẽ biểu đồ
    branch_stats = df_ai_base.groupby('branch').size().reset_index(name='Số máy')
    dept_stats = df_ai_base.groupby('department').size().reset_index(name='Số máy')

    return ai_metrics, df_ai_base, pd.DataFrame(), branch_stats, dept_stats, pd.DataFrame()
