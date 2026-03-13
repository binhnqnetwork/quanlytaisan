import pandas as pd
import numpy as np


def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):

    # -------------------------------------------------
    # 1. INIT
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
    # 2. CLEAN FUNCTION (ENTERPRISE SAFE)
    # -------------------------------------------------

    def clean_code(series):

        s = (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
        )

        s = s.replace(
            ['nan', 'None', 'null', '<NA>', '', 'NaN'],
            np.nan
        )

        return s

    df_assets = df_assets.copy()

    if 'assigned_to_code' in df_assets.columns:
        df_assets['assigned_to_code'] = clean_code(df_assets['assigned_to_code']).astype("string")

    # -------------------------------------------------
    # 3. MERGE STAFF
    # -------------------------------------------------

    if df_staff is not None and not df_staff.empty:

        df_staff = df_staff.copy()

        df_staff['employee_code'] = clean_code(df_staff['employee_code']).astype("string")

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
    # 4. ENSURE COLUMNS
    # -------------------------------------------------

    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = None

    # -------------------------------------------------
    # 5. ASSET STATE CLASSIFICATION
    # -------------------------------------------------

    mask_stock = df_ai_base['assigned_to_code'].isna()

    mask_mismatch = (
        df_ai_base['assigned_to_code'].notna() &
        df_ai_base['full_name'].isna()
    )

    # STOCK
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_stock, 'department'] = 'Lưu kho'
    df_ai_base.loc[mask_stock, 'branch'] = 'Toàn quốc'

    # MISMATCH
    df_ai_base.loc[mask_mismatch, 'full_name'] = (
        '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    )

    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 6. TIME HANDLING (FIX TZ BUG)
    # -------------------------------------------------

    now = pd.Timestamp.now(tz="UTC")

    if 'created_at' in df_ai_base.columns:

        df_ai_base['created_at'] = pd.to_datetime(
            df_ai_base['created_at'],
            errors="coerce",
            utc=True
        ).fillna(now)

    else:

        df_ai_base['created_at'] = now

    df_ai_base['age_days'] = (now - df_ai_base['created_at']).dt.days

    # -------------------------------------------------
    # 7. MAINTENANCE
    # -------------------------------------------------

    if 'maintenance_history' in df_ai_base.columns:

        df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
            lambda x: len(x) if isinstance(x, list) else 0
        )

    else:

        df_ai_base['m_count'] = 0

    # -------------------------------------------------
    # 8. SPEC RISK MODEL
    # -------------------------------------------------

    def get_spec_risk(spec):

        s = str(spec).lower()

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

    # -------------------------------------------------
    # 10. KPI
    # -------------------------------------------------

    ai_metrics["critical_assets"] = int(
        (df_ai_base["risk_level"] == "🔴 Nguy cấp").sum()
    )

    ai_metrics["high_risk_assets"] = int(
        (df_ai_base["risk_level"] == "🟠 Cao").sum()
    )

    # -------------------------------------------------
    # 11. LICENSE ANALYSIS
    # -------------------------------------------------

    if df_lic is not None and not df_lic.empty:

        df_lic = df_lic.copy()

        df_lic['expiry_date'] = pd.to_datetime(
            df_lic['expiry_date'],
            errors='coerce',
            utc=True
        )

        license_ai = df_lic.copy()

        license_ai['days_left'] = (
            license_ai['expiry_date'] - now
        ).dt.days

        ai_metrics["license_alerts"] = int(
            (license_ai['days_left'] < 30).sum()
        )

    # -------------------------------------------------
    # 12. AGGREGATION
    # -------------------------------------------------

    branch_stats = (
        df_ai_base.groupby('branch', dropna=False)
        .agg(
            asset_count=('asset_tag', 'count'),
            avg_risk=('risk_score', 'mean')
        )
        .reset_index()
    )

    dept_stats = (
        df_ai_base.groupby('department', dropna=False)
        .agg(
            asset_count=('asset_tag', 'count'),
            avg_risk=('risk_score', 'mean')
        )
        .reset_index()
    )

    user_stats = (
        df_ai_base.groupby('full_name', dropna=False)
        .agg(
            assets=('asset_tag', 'count'),
            avg_risk=('risk_score', 'mean')
        )
        .sort_values("assets", ascending=False)
        .reset_index()
    )

    # -------------------------------------------------

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
