import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - ENTERPRISE EDITION.
    Sửa lỗi thụt dòng và tối ưu logic Merge/Risk.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    
    # Khởi tạo DataFrame rỗng để tránh lỗi trả về None
    df_ai_base = pd.DataFrame()
    license_ai = pd.DataFrame()
    branch_stats = pd.DataFrame()
    dept_stats = pd.DataFrame()
    user_stats = pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA MÃ (CLEAN CODE)
    # -------------------------------------------------
    def clean_code(series):
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Fix lỗi float .0
            .str.strip()
            .replace(['nan', 'None', 'null', '<NA>', ''], np.nan)
        )

    df_assets = df_assets.copy()
    df_assets['assigned_to_code'] = clean_code(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. MERGE STAFF & XỬ LÝ TRẠNG THÁI
    # -------------------------------------------------
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['employee_code'] = clean_code(df_staff['employee_code'])
        
        # Merge để lấy tên nhân viên
        df_ai_base = pd.merge(
            df_assets,
            df_staff[['employee_code', 'full_name', 'department', 'branch']],
            left_on='assigned_to_code',
            right_on='employee_code',
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()

    # Đảm bảo các cột hiển thị luôn tồn tại
    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = np.nan

    # Phân loại trạng thái
    mask_stock = df_ai_base['assigned_to_code'].isna()
    mask_mismatch = df_ai_base['assigned_to_code'].notna() & df_ai_base['full_name'].isna()

    # Gán nhãn Kho tổng
    df_ai_base.loc[mask_stock, ['full_name', 'department', 'branch']] = ['📦 Kho tổng / Hệ thống', 'Lưu kho', 'Toàn quốc']

    # Gán nhãn Lỗi mã (Khi merge không ra kết quả)
    df_ai_base.loc[mask_mismatch, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 4. XỬ LÝ THỜI GIAN & BẢO TRÌ
    # -------------------------------------------------
    now = pd.Timestamp.now(tz="UTC")

    # Xử lý ngày tạo
    if 'created_at' in df_ai_base.columns:
        df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    else:
        df_ai_base["created_at"] = now
    
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # Xử lý số lần bảo trì
    if 'maintenance_history' in df_ai_base.columns:
        df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )
    else:
        df_ai_base['m_count'] = 0

    # -------------------------------------------------
    # 5. RISK MODEL (MÔ HÌNH RỦI RO)
    # -------------------------------------------------
    def get_spec_risk(spec_val):
        s = str(spec_val).lower()
        score = 0.5
        if any(x in s for x in ['i3', '4gb', 'hdd']): score += 0.3
        if any(x in s for x in ['i7', '16gb', 'ssd', 'nvme']): score -= 0.3
        return np.clip(score, 0.1, 1.0)

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk) if 'specs' in df_ai_base.columns else 0.5

    fail_factor = np.minimum(df_ai_base["m_count"] / 4, 1.0)
    age_factor = np.minimum(df_ai_base["age_days"] / (365 * 4), 1.0)

    df_ai_base["risk_score"] = (fail_factor * 0.4) + (age_factor * 0.3) + (df_ai_base['spec_score'] * 0.3)

    # Phân cấp rủi ro
    conds = [df_ai_base["risk_score"] >= 0.75, df_ai_base["risk_score"] >= 0.45]
    df_ai_base["risk_level"] = np.select(conds, ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp")

    # Cập nhật KPI metrics
    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_level"] == "🟠 Cao").sum())

    # -------------------------------------------------
    # 6. MTBF / MTTR
    # -------------------------------------------------
    if df_maint is not None and not df_maint.empty:
        df_maint['date'] = pd.to_datetime(df_maint['date'], errors='coerce')
        # Sửa lỗi diff() khi tính MTBF
        mtbf_val = df_maint.sort_values(['asset_tag', 'date']).groupby('asset_tag')['date'].diff().dt.days.mean()
        ai_metrics["mtbf"] = f"{round(mtbf_val, 1)} ngày" if pd.notna(mtbf_val) else "N/A"

        if 'repair_time_hours' in df_maint.columns:
            mttr_val = df_maint['repair_time_hours'].mean()
            ai_metrics["mttr"] = f"{round(mttr_val, 1)}h"

    # -------------------------------------------------
    # 7. LICENSE & THỐNG KÊ
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        df_lic['expiry_date'] = pd.to_datetime(df_lic['expiry_date'], errors='coerce')
        days_left = (df_lic['expiry_date'] - now).dt.days
        license_ai = df_lic.assign(days_left=days_left)
        ai_metrics["license_alerts"] = int((days_left < 30).sum())

    # Tổng hợp thống kê
    branch_stats = df_ai_base.groupby('branch', dropna=False).agg(
        asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')
    ).reset_index()

    dept_stats = df_ai_base.groupby('department', dropna=False).agg(
        asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')
    ).reset_index()

    user_stats = df_ai_base.groupby('full_name', dropna=False).agg(
        assets=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')
    ).sort_values("assets", ascending=False).reset_index()

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
