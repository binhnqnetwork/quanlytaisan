import pandas as pd
import numpy as np
import re


def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):

    # =====================================================
    # 1. SYSTEM INIT
    # =====================================================

    ai_metrics = {
        "mtbf": "N/A",
        "mttr": "N/A",
        "critical_assets": 0,
        "high_risk_assets": 0,
        "license_alerts": 0
    }

    empty = pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, empty, empty, empty, empty, empty

    df_assets = df_assets.copy()

    # =====================================================
    # 2. ENSURE REQUIRED COLUMNS
    # =====================================================

    required_columns = [
        "asset_tag",
        "assigned_to_code",
        "created_at"
    ]

    for col in required_columns:
        if col not in df_assets.columns:
            df_assets[col] = np.nan

    # =====================================================
    # 3. ENTERPRISE DATA CLEANING
    # =====================================================

    def super_clean(series):

        if series is None:
            return pd.Series(dtype="object")

        cleaned = (
            series.astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.replace(r"[^\d]", "", regex=True)
        )

        cleaned = cleaned.replace(
            ["", "nan", "None", "null", "<NA>"],
            np.nan
        )

        return cleaned

    # normalize asset code
    df_assets["key_join"] = super_clean(df_assets["assigned_to_code"])

    # backup original department/branch
    if "department" in df_assets.columns:
        df_assets["orig_dept"] = df_assets["department"]

    if "branch" in df_assets.columns:
        df_assets["orig_branch"] = df_assets["branch"]

    # =====================================================
    # 4. STAFF LOOKUP (ENTERPRISE SAFE MERGE)
    # =====================================================

    if df_staff is not None and not df_staff.empty:

        df_staff = df_staff.copy()

        required_staff_cols = [
            "employee_code",
            "full_name",
            "department",
            "branch"
        ]

        for col in required_staff_cols:
            if col not in df_staff.columns:
                df_staff[col] = np.nan

        df_staff["key_staff"] = super_clean(df_staff["employee_code"])

        staff_lookup = (
            df_staff[
                ["key_staff", "full_name", "department", "branch"]
            ]
            .drop_duplicates("key_staff")
        )

        df_ai_base = pd.merge(
            df_assets,
            staff_lookup,
            left_on="key_join",
            right_on="key_staff",
            how="left",
            validate="m:1"
        )

    else:

        df_ai_base = df_assets.copy()

        for col in ["full_name", "department", "branch"]:
            df_ai_base[col] = np.nan

    # =====================================================
    # 5. CLASSIFICATION ENGINE
    # =====================================================

    raw_code = (
        df_ai_base["assigned_to_code"]
        .astype(str)
        .str.strip()
        .replace(["nan", "None", ""], np.nan)
    )

    is_empty_code = raw_code.isna()

    # ---------- STOCK / SYSTEM ----------
    mask_stock = is_empty_code

    df_ai_base.loc[mask_stock, "full_name"] = "📦 Kho tổng / Hệ thống"

    if "orig_dept" in df_ai_base.columns:
        df_ai_base.loc[mask_stock, "department"] = (
            df_ai_base.loc[mask_stock, "orig_dept"]
            .fillna("Lưu kho")
        )
    else:
        df_ai_base.loc[mask_stock, "department"] = "Lưu kho"

    df_ai_base.loc[mask_stock, "branch"] = "Toàn quốc"

    # ---------- STAFF CODE ERROR ----------
    mask_error = (~is_empty_code) & (df_ai_base["full_name"].isna())

    df_ai_base.loc[mask_error, "full_name"] = (
        "⚠️ Lỗi: Mã " +
        df_ai_base["assigned_to_code"].astype(str)
    )

    df_ai_base.loc[mask_error, "department"] = "Cần rà soát"
    df_ai_base.loc[mask_error, "branch"] = "Chưa xác định"

    # =====================================================
    # 6. TIME ENGINE (TZ SAFE)
    # =====================================================

    now = pd.Timestamp.now(tz="UTC")

    df_ai_base["created_at"] = pd.to_datetime(
        df_ai_base["created_at"],
        errors="coerce",
        utc=True
    ).fillna(now)

    df_ai_base["age_days"] = (
        now - df_ai_base["created_at"]
    ).dt.days

    # =====================================================
    # 7. RISK ENGINE (ENTERPRISE MODEL)
    # =====================================================

    # maintenance count
    if "maintenance_history" in df_ai_base.columns:

        df_ai_base["m_count"] = df_ai_base["maintenance_history"].apply(
            lambda x: len(x)
            if isinstance(x, list)
            else 0
        )

    else:
        df_ai_base["m_count"] = 0

    # age factor
    age_factor = np.minimum(
        df_ai_base["age_days"] / (365 * 4),
        1
    )

    fail_factor = np.minimum(
        df_ai_base["m_count"] / 4,
        1
    )

    df_ai_base["risk_score"] = (
        fail_factor * 0.5 +
        age_factor * 0.5
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

    ai_metrics["high_risk_assets"] = int(
        (df_ai_base["risk_level"] == "🟠 Cao").sum()
    )

    # =====================================================
    # 8. LICENSE ENGINE
    # =====================================================

    license_ai = pd.DataFrame()

    if "license_expiry" in df_ai_base.columns:

        df_ai_base["license_expiry"] = pd.to_datetime(
            df_ai_base["license_expiry"],
            errors="coerce"
        )

        license_ai = df_ai_base[
            df_ai_base["license_expiry"]
            < (pd.Timestamp.today() + pd.Timedelta(days=30))
        ]

        ai_metrics["license_alerts"] = len(license_ai)

    # =====================================================
    # 9. ENTERPRISE ANALYTICS
    # =====================================================

    branch_stats = (
        df_ai_base
        .groupby("branch")
        .agg(
            asset_count=("asset_tag", "count"),
            avg_risk=("risk_score", "mean")
        )
        .reset_index()
    )

    dept_stats = (
        df_ai_base
        .groupby("department")
        .agg(
            asset_count=("asset_tag", "count"),
            avg_risk=("risk_score", "mean")
        )
        .reset_index()
    )

    user_stats = (
        df_ai_base
        .groupby("full_name")
        .agg(
            assets=("asset_tag", "count"),
            avg_risk=("risk_score", "mean")
        )
        .sort_values("assets", ascending=False)
        .reset_index()
    )

    # =====================================================
    # 10. DEBUG ENGINE (Enterprise monitoring)
    # =====================================================

    try:

        unmatched = set(
            df_assets["key_join"].dropna()
        ) - set(
            df_staff["key_staff"].dropna()
        )

        if len(unmatched) > 0:
            print("⚠️ STAFF CODE MISMATCH:", unmatched)

    except:
        pass

    return (
        ai_metrics,
        df_ai_base,
        license_ai,
        branch_stats,
        dept_stats,
        user_stats
    )
