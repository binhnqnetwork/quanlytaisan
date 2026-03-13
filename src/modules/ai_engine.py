import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - ENTERPRISE EDITION.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    df_ai_base = pd.DataFrame()
    license_ai = pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA MÃ GỐC (Sử dụng Regex để loại bỏ ký tự lạ)
    # -------------------------------------------------
    def clean_code(series):
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Xóa .0 nếu là float
            .str.strip()
            .replace(['nan', 'None', 'null', '<NA>', ''], np.nan)
        )

    df_assets = df_assets.copy()
    df_assets['assigned_to_code'] = clean_code(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. THỰC HIỆN MERGE
    # -------------------------------------------------
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['employee_code'] = clean_code(df_staff['employee_code'])
        
        staff_cols = ['employee_code', 'full_name', 'department', 'branch']
        existing_cols = [c for c in staff_cols if c in df_staff.columns]
        
        df_ai_base = pd.merge(
            df_assets, 
            df_staff[existing_cols], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()

    # -------------------------------------------------
    # 4. XỬ LÝ DỮ LIỆU SAU MERGE (Gợi ý fix triệt để)
    # -------------------------------------------------
    # Đảm bảo các cột tồn tại để không bị lỗi Dashboard
    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = None

    # Phân loại 3 trạng thái của tài sản:
    # Trạng thái 1: Máy đang ở Kho (Không có mã assign)
    mask_stock = df_ai_base['assigned_to_code'].isna()
    
    # Trạng thái 2: Lỗi khớp mã (Có mã nhưng merge xong full_name vẫn trống)
    mask_mismatch = df_ai_base['assigned_to_code'].notna() & df_ai_base['full_name'].isna()

    # Gán giá trị Kho tổng
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # Gán giá trị Lỗi dữ liệu (Để bạn biết máy nào cần sửa mã nhân viên)
    df_ai_base.loc[mask_mismatch, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 5. PHÂN TÍCH RỦI RO & KPI (Giữ nguyên logic của bạn)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
        lambda x: len(x) if isinstance(x, list) else (0 if pd.isna(x) else 1)
    )
    
    # Tính Risk Score
    def get_spec_risk(spec_val):
        s = str(spec_val).lower()
        score = 0.5
        if any(x in s for x in ['i3', '4gb', 'hdd']): score += 0.3
        if any(x in s for x in ['i7', '16gb', 'ssd']): score -= 0.3
        return np.clip(score, 0.1, 1.0)

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)
    fail_factor = np.minimum(df_ai_base["m_count"] / 4, 1.0)
    age_factor = np.minimum(df_ai_base["age_days"] / (365 * 4), 1.0)
    df_ai_base["risk_score"] = (fail_factor * 0.4) + (age_factor * 0.3) + (df_ai_base['spec_score'] * 0.3)
    
    conds = [df_ai_base["risk_score"] >= 0.75, df_ai_base["risk_score"] >= 0.45]
    df_ai_base["risk_level"] = np.select(conds, ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp")

    # Thống kê
    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    
    # -------------------------------------------------
    # 6. LICENSE & AGGREGATION
    # -------------------------------------------------
    branch_stats = df_ai_base.groupby('branch').agg({'asset_tag': 'count', 'risk_score': 'mean'}).reset_index()
    dept_stats = df_ai_base.groupby('department').agg({'asset_tag': 'count', 'risk_score': 'mean'}).reset_index()

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
