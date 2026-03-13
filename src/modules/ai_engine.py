import pandas as pd
import numpy as np


def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - ENTERPRISE EDITION
    """

    # -------------------------------------------------
    # 1. KHỞI TẠO
    # -------------------------------------------------

    ai_metrics = {
        "mtbf": "N/A",
        "mttr": "N/A",
        "critical_assets": 0,
        "high_risk_assets": 0,
        "license_alerts": 0
    }

    df_ai_base = pd.DataFrame()
    license_ai = pd.DataFrame()
    branch_stats = pd.DataFrame()
    dept_stats = pd.DataFrame()
    user_stats = pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. HÀM CHUẨN HÓA MÃ
    # -------------------------------------------------

    def clean_code(series):
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
            .replace(['nan', 'None', 'null', '<NA>', ''], np.nan)
        )

    df_assets = df_assets.copy()
    df_assets['assigned_to_code'] = clean_code(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. MERGE STAFF
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
    # 4. ĐẢM BẢO CỘT TỒN TẠI
    # -------------------------------------------------

    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = None

    # -------------------------------------------------
    # 5. PHÂN LOẠI TRẠNG THÁI
    # -------------------------------------------------

    mask_stock = df_ai_base['assigned_to_code'].isna()

    mask_mismatch = (
        df_ai_base['assigned_to_code'].notna() &
        df_ai_base['full_name'].isna()
    )

    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    df_ai_base.loc[mask_mismatch, 'full_name'] = (
        '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    )
    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 6. CHUẨN HÓA THỜI GIAN
    # -------------------------------------------------

    now = pd.Timestamp.utcnow()

    if 'created_at' in df_ai_base.columns:
        df_ai_base["created_at"] = pd.to_datetime(
            df_ai_base["created_at"],
            errors="coerce",
            utc=True
        ).fillna(now)
    else:
        df_ai_base["created_at"] = now

    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # -------------------------------------------------
    # 7. MAINTENANCE ANALYTICS
    # -------------------------------------------------

    if 'maintenance_history' in df_ai_base.columns:

        df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )

    else:
        df_ai_base['m_count'] = 0

    # -------------------------------------------------
    # 8. SPEC ANALYSIS
    # -------------------------------------------------

    def get_spec_risk(spec_val):

        s = str(spec_val).lower()

        score = 0.5

        if any(x in s for x in ['i3', '4gb', 'hdd']):
            score += 0.3

        if any(x in s for x in ['i7', '16gb', 'ssd', 'nvme']):
            score -= 0.3

        return np.clip(score, 0.1, 1.0)

    if 'specs' in df_ai_base.columns:
        df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)
    else:
        df_ai_base['spec_score'] = 0.5

    # -------------------------------------------------
    # 9. RISK MODEL
    # -------------------------------------------------

    fail_factor = np.minimum(df_ai_base["m_count"] / 4, 1.0)
    age_factor = np.minimum(df_ai_base["age_days"] / (365 * 4), 1.0)

    df_ai_base["risk_score"] = (
        (fail_factor * 0.4)
        + (age_factor * 0.3)
        + (df_ai_base['spec_score'] * 0.3)
    )

    conds = [
        df_ai_base["risk_score"] >= 0.75,
        df_ai_base["risk_score"] >= 0.45
    ]

    df_ai_base["risk_level"] = np.select(
        conds,
        ["🔴 Nguy cấp", "🟠 Cao"],
        default="🟢 Thấp"
    )

    ai_metrics["critical_assets"] = int(
        (df_ai_base["risk_level"] == "🔴 Nguy cấp").sum()
    )

    # -------------------------------------------------
    # 10. AGGREGATION
    # -------------------------------------------------

    branch_stats = (
        df_ai_base.groupby('branch', dropna=False)
        .agg({'asset_tag': 'count', 'risk_score': 'mean'})
        .reset_index()
    )

    dept_stats = (
        df_ai_base.groupby('department', dropna=False)
        .agg({'asset_tag': 'count', 'risk_score': 'mean'})
        .reset_index()
    )

    # -------------------------------------------------

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
