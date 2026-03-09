import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    # Khởi tạo các giá trị mặc định theo chuẩn Apple UI
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
    # 1. DATA PREPARATION (Đồng bộ asset_tag)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Chuyển đổi thời gian created_at
    df_assets["created_at"] = pd.to_datetime(
        df_assets["created_at"], errors="coerce", utc=True
    )
    
    # Nếu created_at lỗi, dùng thời điểm hiện tại để tránh crash
    df_assets["created_at"] = df_assets["created_at"].fillna(now)
    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days

    # -------------------------------------------------
    # 2. MAINTENANCE ANALYTICS (Fix asset_tag)
    # -------------------------------------------------
    if not df_maint.empty:
        df_maint = df_maint.copy()
        df_maint["performed_at"] = pd.to_datetime(
            df_maint["performed_at"], errors="coerce", utc=True
        )

        # Đếm số lần hỏng dựa trên asset_tag
        maint_counts = df_maint.groupby("asset_tag").size().reset_index(name="m_count")
        
        # Ngày hỏng gần nhất
        last_fail = df_maint.groupby("asset_tag")["performed_at"].max().reset_index(name="last_failure")

        # Tính MTTR (Trung vị thời gian sửa chữa)
        if "duration" in df_maint.columns:
            mttr = df_maint["duration"].median()
            ai_metrics["mttr"] = f"{mttr:.1f} hrs"
    else:
        maint_counts = pd.DataFrame(columns=["asset_tag", "m_count"])
        last_fail = pd.DataFrame(columns=["asset_tag", "last_failure"])

    # -------------------------------------------------
    # 3. SMART MERGE (Xóa bỏ hoàn toàn asset_id)
    # -------------------------------------------------
    df_ai = pd.merge(df_assets, maint_counts, on="asset_tag", how="left")
    df_ai = pd.merge(df_ai, last_fail, on="asset_tag", how="left")

    df_ai["m_count"] = df_ai["m_count"].fillna(0)
    df_ai["last_failure"] = pd.to_datetime(df_ai["last_failure"], errors="coerce", utc=True)

    # Nếu chưa hỏng bao giờ, mặc định là 9999 ngày để Risk Score thấp
    df_ai["days_since_failure"] = (now - df_ai["last_failure"]).dt.days
    df_ai["days_since_failure"] = df_ai["days_since_failure"].fillna(9999)

    # -------------------------------------------------
    # 4. FEATURE ENGINEERING & RISK MODEL
    # -------------------------------------------------
    # Age factor: Máy trên 3 năm (1095 ngày) đạt điểm tối đa
    age_factor = np.minimum(df_ai["age_days"] / 1095, 1)
    
    # Failure factor: Hỏng trên 5 lần đạt điểm tối đa
    failure_factor = np.minimum(df_ai["m_count"] / 5, 1)
    
    # Recent failure: Hỏng trong vòng 1 năm qua
    recent_failure = np.maximum(0, 1 - df_ai["days_since_failure"] / 365)

    # Công thức Risk Score (Trọng số 40-40-20)
    df_ai["risk_score"] = (0.4 * failure_factor + 0.4 * age_factor + 0.2 * recent_failure)
    df_ai["risk_score"] = np.clip(df_ai["risk_score"], 0, 1)

    # Failure Probability (Sigmoid function)
    df_ai["failure_probability"] = 1 / (1 + np.exp(-6 * (df_ai["risk_score"] - 0.5)))

    # Phân loại rủi ro
    df_ai["risk_level"] = np.select(
        [df_ai["risk_score"] >= 0.8, df_ai["risk_score"] >= 0.6, df_ai["risk_score"] >= 0.4],
        ["Critical", "High", "Medium"], default="Low"
    )

    # -------------------------------------------------
    # 5. LICENSE ANALYTICS (Fix tên cột 'name')
    # -------------------------------------------------
    if not df_lic.empty:
        license_ai = df_lic.copy()
        # Sử dụng đúng tên cột thực tế của bạn
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).fillna(0)
        
        license_ai["license_risk"] = np.select(
            [license_ai["usage_ratio"] > 0.95, license_ai["usage_ratio"] > 0.8],
            ["Critical", "Warning"], default="Healthy"
        )

    # -------------------------------------------------
    # 6. FINAL SUMMARY
    # -------------------------------------------------
    ai_metrics["critical_assets"] = int((df_ai["risk_level"] == "Critical").sum())
    ai_metrics["high_risk_assets"] = int((df_ai["risk_level"] == "High").sum())
    
    if not df_maint.empty:
        total_op = df_ai["age_days"].sum()
        if df_maint.shape[0] > 0:
            mtbf = total_op / df_maint.shape[0]
            ai_metrics["mtbf"] = f"{int(mtbf)} days"

    return ai_metrics, df_ai, license_ai
