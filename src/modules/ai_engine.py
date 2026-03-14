import pandas as pd
import numpy as np
import re

def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):
    # --- 1. KHỞI TẠO ---
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- 2. HÀM CƯỠNG CHẾ KHỚP MÃ (FORCE MATCH) ---
    def force_match_clean(series):
        if series is None: return np.nan
        # Bước 1: Ép về string và xóa .0
        s = series.astype(str).str.replace(r'\.0$', '', regex=True)
        # Bước 2: CHỈ lấy các chữ số (0-9). Xóa sạch mọi thứ khác kể cả khoảng trắng ẩn, \n, \t
        s = s.str.extract(r'(\d+)', expand=False)
        return s.replace(['nan', 'None', ''], np.nan)

    df_assets = df_assets.copy()
    if 'department' in df_assets.columns: df_assets['orig_dept'] = df_assets['department']
    
    # Tạo khóa liên kết siêu sạch
    df_assets['key_join'] = force_match_clean(df_assets['assigned_to_code'])

    # --- 3. STAFF LOOKUP ---
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['key_staff'] = force_match_clean(df_staff['employee_code'])
        
        # Loại bỏ trùng lặp và chỉ lấy cột cần thiết
        staff_lookup = df_staff[['key_staff', 'full_name', 'department', 'branch']].drop_duplicates('key_staff')

        # THỰC HIỆN MERGE
        df_ai_base = pd.merge(df_assets, staff_lookup, left_on='key_join', right_on='key_staff', how='left')
    else:
        df_ai_base = df_assets.copy()
        for col in ['full_name', 'department', 'branch']: df_ai_base[col] = np.nan

    # --- 4. PHÂN LOẠI HIỂN THỊ ---
    # Kiểm tra mã gốc (Sử dụng trực tiếp assigned_to_code để phân biệt)
    raw_val = df_ai_base['assigned_to_code'].astype(str).str.strip().replace(['nan', 'None', '', '<NA>'], np.nan)
    is_empty = raw_val.isna()

    # Case: Kho tổng
    df_ai_base.loc[is_empty, 'full_name'] = '📦 Kho tổng / Hệ thống'
    if 'orig_dept' in df_ai_base.columns:
        df_ai_base.loc[is_empty, 'department'] = df_ai_base.loc[is_empty, 'orig_dept'].fillna('Lưu kho')
    else:
        df_ai_base.loc[is_empty, 'department'] = 'Lưu kho'
    df_ai_base.loc[is_empty, 'branch'] = 'Toàn quốc'

    # Case: Lỗi (Có mã nhưng không khớp được tên)
    mask_error = (~is_empty) & (df_ai_base['full_name'].isna())
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # --- 5. RISK & STATS (Giữ nguyên logic của bạn) ---
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base['risk_score'] = 0.2
    df_ai_base['risk_level'] = "🟢 Thấp"
    
    branch_stats = df_ai_base.groupby('branch').size().reset_index(name='asset_count')
    dept_stats = df_ai_base.groupby('department').size().reset_index(name='asset_count')
    user_stats = df_ai_base.groupby('full_name').size().reset_index(name='assets').sort_values('assets', ascending=False)

    return ai_metrics, df_ai_base, pd.DataFrame(), branch_stats, dept_stats, user_stats
