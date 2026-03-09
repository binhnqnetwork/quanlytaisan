import pandas as pd
import numpy as np

def calculate_ai_metrics_v2(df_assets, df_maint, df_lic):

    ai_metrics = {
        "mtbf": "N/A",
        "mttr": "N/A",
        "critical_assets": 0,
        "high_risk_assets": 0
    }

    df_ai = pd.DataFrame()
    license_ai = pd.DataFrame()

    if df_assets.empty:
        return ai_metrics, df_ai, license_ai

    # -------------------------------------------------
    # 1. DATA PREPARATION
    # -------------------------------------------------

    now = pd.Timestamp.utcnow()

    df_assets = df_assets.copy()

    df_assets["created_at"] = pd.to_datetime(
        df_assets["created_at"],
        errors="coerce",
        utc=True
    )

    df_assets = df_assets.dropna(subset=["created_at"])

    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days

    # -------------------------------------------------
    # 2. MAINTENANCE ANALYTICS
    # -------------------------------------------------

    if not df_maint.empty:

        df_maint = df_maint.copy()

        df_maint["performed_at"] = pd.to_datetime(
            df_maint["performed_at"],
            errors="coerce",
            utc=True
        )

        # Failure count
        maint_counts = (
            df_maint.groupby("asset_tag")
            .size()
            .reset_index(name="m_count")
        )

        # Last failure date
        last_fail = (
            df_maint.groupby("asset_tag")["performed_at"]
            .max()
            .reset_index(name="last_failure")
        )

        # MTTR
        if "duration" in df_maint.columns:
            mttr = df_maint["duration"].median()
            ai_metrics["mttr"] = f"{mttr:.1f} hrs"

    else:

        maint_counts = pd.DataFrame(columns=["asset_tag","m_count"])
        last_fail = pd.DataFrame(columns=["asset_tag","last_failure"])

    # -------------------------------------------------
    # 3. MERGE DATA
    # -------------------------------------------------

    df_ai = pd.merge(df_assets, maint_counts, on="asset_tag", how="left")
    df_ai = pd.merge(df_ai, last_fail, on="asset_tag", how="left")

    df_ai["m_count"] = df_ai["m_count"].fillna(0)

    df_ai["last_failure"] = pd.to_datetime(
        df_ai["last_failure"],
        errors="coerce",
        utc=True
    )

    df_ai["days_since_failure"] = (now - df_ai["last_failure"]).dt.days
    df_ai["days_since_failure"] = df_ai["days_since_failure"].fillna(9999)

    # -------------------------------------------------
    # 4. FEATURE ENGINEERING
    # -------------------------------------------------

    # Age factor (max 3 years)
    age_factor = np.minimum(df_ai["age_days"] / 1095, 1)

    # Failure frequency
    failure_factor = np.minimum(df_ai["m_count"] / 5, 1)

    # Recent failure factor
    recent_failure = np.maximum(0, 1 - df_ai["days_since_failure"] / 365)

    # -------------------------------------------------
    # 5. RISK SCORE MODEL
    # -------------------------------------------------

    df_ai["risk_score"] = (
        0.4 * failure_factor +
        0.4 * age_factor +
        0.2 * recent_failure
    )

    df_ai["risk_score"] = np.clip(df_ai["risk_score"], 0, 1)

    # -------------------------------------------------
    # 6. FAILURE PROBABILITY
    # -------------------------------------------------

    df_ai["failure_probability"] = 1 / (
        1 + np.exp(-6 * (df_ai["risk_score"] - 0.5))
    )

    # -------------------------------------------------
    # 7. RISK CLASSIFICATION
    # -------------------------------------------------

    conditions = [
        df_ai["risk_score"] >= 0.8,
        df_ai["risk_score"] >= 0.6,
        df_ai["risk_score"] >= 0.4
    ]

    levels = ["Critical", "High", "Medium"]

    df_ai["risk_level"] = np.select(
        conditions,
        levels,
        default="Low"
    )

    # -------------------------------------------------
    # 8. REPLACEMENT PREDICTION
    # -------------------------------------------------

    df_ai["replacement_score"] = np.minimum(df_ai["age_days"] / 1460, 1)

    # -------------------------------------------------
    # 9. MTBF CALCULATION
    # -------------------------------------------------

    if not df_maint.empty:

        total_operating_days = df_ai["age_days"].sum()
        total_failures = df_maint.shape[0]

        if total_failures > 0:

            mtbf = total_operating_days / total_failures
            ai_metrics["mtbf"] = f"{int(mtbf)} days"

    # -------------------------------------------------
    # 10. LICENSE ANALYTICS
    # -------------------------------------------------

    if not df_lic.empty:

        license_ai = df_lic.copy()

        license_ai["usage_ratio"] = (
            license_ai["used_quantity"] /
            license_ai["total_quantity"]
        )

        license_ai["usage_ratio"] = license_ai["usage_ratio"].fillna(0)

        license_ai["license_pressure"] = np.clip(
            license_ai["usage_ratio"], 0, 1
        )

        license_ai["license_risk"] = np.select(
            [
                license_ai["usage_ratio"] > 0.9,
                license_ai["usage_ratio"] > 0.75
            ],
            ["Critical","Warning"],
            default="Healthy"
        )

    # -------------------------------------------------
    # 11. SUMMARY METRICS
    # -------------------------------------------------

    ai_metrics["critical_assets"] = int(
        (df_ai["risk_level"] == "Critical").sum()
    )

    ai_metrics["high_risk_assets"] = int(
        (df_ai["risk_level"] == "High").sum()
    )

    return ai_metrics, df_ai, license_ai
