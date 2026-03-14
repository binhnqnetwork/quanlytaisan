import pandas as pd
import numpy as np
import re

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    # --- 1. KHỞI TẠO ---
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A", 
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- 2. HÀM LÀM SẠCH TUYỆT ĐỐI (Dùng cho cả 2 bảng) ---
    def super_clean(series):
        if series is None: return np.nan
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Xử lý lỗi số thực (3140.0 -> 3140)
            .str.replace(r'\D', '', regex=True)    # Chỉ giữ lại chữ số, xóa sạch khoảng trắng/ký tự ẩn
            .replace(['', 'nan', 'None', 'null'], np.nan)
        )

    # --- 3. CHUẨN BỊ DỮ LIỆU ASSETS ---
    df_assets = df_assets.copy()
    
    # Backup lại phòng ban gốc để xử lý trường hợp Kho tổng (như Hạ tầng)
    if 'department' in df_assets.columns:
        df_assets['orig_dept'] = df_assets['department']
    if 'branch' in df_assets.columns:
        df_assets['orig_branch'] = df_assets['branch']

    # Tạo khóa liên kết sạch
    df_assets['key_join'] = super_clean(df_assets['assigned_to_code'])

    # --- 4. MERGE VỚI STAFF (Xử lý lỗi lệch kiểu dữ liệu) ---
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['key_staff'] = super_clean(df_staff['employee_code'])
        
        # Chỉ lấy cột cần thiết và loại bỏ trùng lặp để tránh nhân đôi số lượng máy
        staff_lookup = df_staff[['key_staff', 'full_name', 'department', 'branch']].drop_duplicates('key_staff')

        # Thực hiện kết nối trái (Left Join)
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

    # --- 5. LOGIC PHÂN LOẠI THÔNG MINH ---
    # Kiểm tra mã gốc để phân biệt máy rỗng (Kho) và máy gán sai (Lỗi)
    raw_code = df_ai_base['assigned_to_code'].astype(str).str.strip().replace(['nan', 'None', ''], np.nan)
    is_empty_code = raw_code.isna()

    # TRƯỜNG HỢP 1: KHO TỔNG / HỆ THỐNG (Mã trống)
    mask_stock = is_empty_code
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    # Ưu tiên giữ lại phòng ban 'Hạ tầng' nếu có sẵn
    if 'orig_dept' in df_ai_base.columns:
        df_ai_base.loc[mask_stock, 'department'] = df_ai_base.loc[mask_stock, 'orig_dept'].fillna('Lưu kho')
    else:
        df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # TRƯỜNG HỢP 2: LỖI KHỚP MÃ (Có mã nhưng không tìm thấy trong Staff)
    mask_error = (~is_empty_code) & (df_ai_base['full_name'].isna())
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # --- 6. TÍNH TOÁN RỦI RO & THỜI GIAN ---
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base['created_at'] = pd.to_datetime(df_ai_base.get('created_at', now), errors="coerce", utc=True).fillna(now)
    df_ai_base['age_days'] = (now - df_ai_base['created_at']).dt.days
    
    # Giả lập Risk Score (Bạn có thể thay bằng logic MTBF/MTTR cụ thể)
    df_ai_base["risk_score"] = 0.2 # Mặc định thấp
    df_ai_base["risk_level"] = "🟢 Thấp"

    # --- 7. AGGREGATION (THỐNG KÊ) ---
    branch_stats = df_ai_base.groupby('branch').agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    dept_stats = df_ai_base.groupby('department').agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    user_stats = df_ai_base.groupby('full_name').agg(assets=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).sort_values("assets", ascending=False).reset_index()

    return ai_metrics, df_ai_base, pd.DataFrame(), branch_stats, dept_stats, user_stats
