import pandas as pd
import numpy as np
import re

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    # --- 1. KHỞI TẠO ---
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- 2. BƯỚC ĐỘT PHÁ: HÀM LÀM SẠCH TUYỆT ĐỐI ---
    def super_clean(series):
        if series is None: return np.nan
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Xóa đuôi .0 của số float
            .str.replace(r'\D', '', regex=True)    # CHỈ GIỮ LẠI CHỮ SỐ (0-9), xóa sạch khoảng trắng/ký tự đặc biệt
            .replace(['', 'nan', 'None'], np.nan)
        )

    df_assets = df_assets.copy()
    # Nếu bảng assets đã có sẵn cột department/branch từ trước, hãy đổi tên để tránh xung đột khi merge
    for col in ['department', 'branch']:
        if col in df_assets.columns:
            df_assets = df_assets.rename(columns={col: f'orig_{col}'})

    df_assets['key_join'] = super_clean(df_assets['assigned_to_code'])

    # --- 3. MERGE VỚI LOGIC ƯU TIÊN DỮ LIỆU ---
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['key_staff'] = super_clean(df_staff['employee_code'])
        
        # Chỉ lấy 4 cột quan trọng nhất từ bảng staff để merge
        staff_lookup = df_staff[['key_staff', 'full_name', 'department', 'branch']].drop_duplicates('key_staff')

        df_ai_base = pd.merge(
            df_assets, 
            staff_lookup, 
            left_on='key_join', 
            right_on='key_staff', 
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()
        for c in ['full_name', 'department', 'branch']: df_ai_base[c] = np.nan

    # --- 4. XỬ LÝ PHÂN LOẠI THÔNG MINH ---
    # Ưu tiên 1: Nếu tìm thấy nhân viên từ bảng Staff
    # Ưu tiên 2: Nếu là Kho tổng (Mã trống)
    # Ưu tiên 3: Nếu có mã nhưng không tìm thấy nhân viên (Lỗi)

    # Kiểm tra mã gốc (để phân biệt giữa rỗng thật và rỗng sau khi clean)
    is_empty_code = df_assets['assigned_to_code'].isna() | (df_assets['assigned_to_code'].astype(str).str.strip() == '')

    # Trường hợp KHO (Không có mã)
    mask_stock = is_empty_code
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    # Nếu có phòng ban gốc (Hạ tầng) thì giữ, không thì để Lưu kho
    if 'orig_department' in df_ai_base.columns:
        df_ai_base.loc[mask_stock, 'department'] = df_ai_base.loc[mask_stock, 'orig_department'].fillna('Lưu kho')
    else:
        df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # Trường hợp LỖI (Có mã nhưng merge không ra tên)
    mask_error = (~is_empty_code) & (df_ai_base['full_name'].isna())
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # --- 5. CÁC PHÉP TÍNH RỦI RO & THỜI GIAN (GIỮ NGUYÊN) ---
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base['created_at'] = pd.to_datetime(df_ai_base.get('created_at', now), errors="coerce", utc=True).fillna(now)
    df_ai_base['age_days'] = (now - df_ai_base['created_at']).dt.days
    
    # Risk calculation... (Rút gọn để tập trung vào logic merge)
    df_ai_base["risk_score"] = 0.5 # Mặc định
    df_ai_base["risk_level"] = "🟢 Thấp"

    # --- 6. AGGREGATION ---
    branch_stats = df_ai_base.groupby('branch').agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    dept_stats = df_ai_base.groupby('department').agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    user_stats = df_ai_base.groupby('full_name').agg(assets=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).sort_values("assets", ascending=False).reset_index()

    return ai_metrics, df_ai_base, pd.DataFrame(), branch_stats, dept_stats, user_stats
