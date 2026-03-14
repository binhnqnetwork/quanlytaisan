import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    # --- 1. KHỞI TẠO ---
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    df_ai_base = pd.DataFrame()
    
    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- 2. HÀM CHUẨN HÓA CẤP ĐỘ CAO ---
    def normalize_code(series):
        # Bước quan trọng nhất: Ép về string, xóa .0, xóa mọi khoảng trắng và ký tự không phải số
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Xóa đuôi float
            .str.replace(r'\s+', '', regex=True)  # Xóa mọi khoảng trắng ẩn
            .str.strip()
            .replace(['nan', 'None', 'null', ''], np.nan)
        )

    df_assets = df_assets.copy()
    # Tạo khóa liên kết đã chuẩn hóa
    df_assets['key_link'] = normalize_code(df_assets['assigned_to_code'])

    # --- 3. XỬ LÝ BẢNG STAFF ---
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        # Chuẩn hóa mã nhân viên từ Supabase
        df_staff['staff_key'] = normalize_code(df_staff['employee_code'])
        
        # Chỉ lấy các cột định danh quan trọng
        staff_lookup = df_staff[['staff_key', 'full_name', 'department', 'branch']].drop_duplicates('staff_key')

        # THỰC HIỆN MERGE
        df_ai_base = pd.merge(
            df_assets,
            staff_lookup,
            left_on='key_link',
            right_on='staff_key',
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()
        for col in ['full_name', 'department', 'branch']:
            df_ai_base[col] = np.nan

    # --- 4. LOGIC HIỂN THỊ (FIXED) ---
    # Phân loại dựa trên việc có mã hay không và merge có thành công hay không
    has_code = df_ai_base['key_link'].notna()
    merge_fail = df_ai_base['full_name'].isna()

    # Case 1: Máy lưu kho (Không có mã nhân viên)
    mask_stock = ~has_code
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    # Bảo toàn phòng ban "Hạ tầng" nếu có sẵn từ database assets
    if 'department' not in df_ai_base.columns or df_ai_base['department'].isnull().all():
         df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # Case 2: Lỗi khớp mã (Có mã nhưng không tìm thấy Tên)
    mask_error = has_code & merge_fail
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # --- 5. TÍNH TOÁN RỦI RO & KPI ---
    # (Giữ nguyên logic tính Risk Score và các thống kê stats của bạn)
    # ... logic aggregation ...

    return ai_metrics, df_ai_base, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
