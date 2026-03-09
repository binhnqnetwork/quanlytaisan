import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    # 1. Khởi tạo giá trị mặc định (Apple UI Style)
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    
    # Khởi tạo các DataFrame rỗng để an toàn khi return
    df_ai, license_ai = pd.DataFrame(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # KIỂM TRA ĐẦU VÀO: Nếu không có tài sản, thoát ngay để tránh lỗi
    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU (KHỚP VỚI DB CỦA BẠN)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Ép kiểu dữ liệu phức tạp sang String để tránh lỗi đệ quy hệ thống
    for col in ['specs', 'software_list', 'maintenance_history']:
        if col in df_assets.columns:
            df_assets[col] = df_assets[col].astype(str)

    # Đồng bộ assigned_to_code từ bảng của bạn
    df_assets['assigned_to'] = df_assets['assigned_to_code'].fillna("Kho tổng") if 'assigned_to_code' in df_assets.columns else "Chưa xác định"

    # AI Heuristics: Tách chi nhánh (PC0001-HCM -> HCM)
    df_assets['branch'] = df_assets['asset_tag'].str.split('-').str[-1].fillna("Khác")
    
    # Suy luận phòng ban
    if 'department' not in df_assets.columns:
        df_assets['department'] = df_assets['type'].apply(
            lambda x: "Hạ tầng Server" if str(x).lower() == 'server' else "Khối Văn phòng"
        )

    df_assets["created_at"] = pd.to_datetime(df_assets["created_at"], errors="coerce", utc=True).fillna(now)
    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR)
    # -------------------------------------------------
    if df_maint is not None and not df_maint.empty:
        df_maint = df_maint.copy()
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        maint_counts = df_maint.groupby("asset_tag").size().reset_index(name="m_count")
        last_fail = df_maint.groupby("asset_tag")["performed_at"].max().reset_index(name="last_failure")
        
        if "duration" in df_maint.columns:
            ai_metrics["mttr"] = f"{df_maint['duration'].median():.1f} hrs"
    else:
        maint_counts = pd.DataFrame(columns=["asset_tag", "m_count"])
        last_fail = pd.DataFrame(columns=["asset_tag", "last_failure"])

    # -------------------------------------------------
    # 4. AI RISK MODEL (SIGMOID PREDICTION)
    # -------------------------------------------------
    df_ai = pd.merge(df_assets, maint_counts, on="asset_tag", how="left")
    df_ai = pd.merge(df_ai, last_fail, on="asset_tag", how="left")

    df_ai["m_count"] = df_ai["m_count"].fillna(0)
    df_ai["days_since_failure"] = (now - pd.to_datetime(df_ai["last_failure"], utc=True)).dt.days.fillna(9999)

    # Risk Calculation
    age_f = np.minimum(df_ai["age_days"] / 1095, 1)
    fail_f = np.minimum(df_ai["m_count"] / 5, 1)
    rec_f = np.maximum(0, 1 - df_ai["days_since_failure"] / 365)

    df_ai["risk_score"] = (0.4 * fail_f + 0.4 * age_f + 0.2 * rec_f)
    df_ai["failure_prob"] = 1 / (1 + np.exp(-6 * (df_ai["risk_score"] - 0.5)))
    
    df_ai["risk_level"] = np.select(
        [df_ai["risk_score"] >= 0.8, df_ai["risk_score"] >= 0.6, df_ai["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao", "🟡 Trung bình"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 5. THỐNG KÊ CHI TIẾT (BRANCH / USER)
    # -------------------------------------------------
    branch_stats = df_ai.groupby('branch').agg({'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'})
    
    dept_stats = df_ai.groupby('department').agg({'m_count': 'sum', 'failure_prob': 'mean'})

    user_stats = df_ai.groupby(['assigned_to', 'department']).agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Lượt hỏng', 'risk_score': 'Rủi ro Max'})
    user_stats = user_stats.sort_values('Lượt hỏng', ascending=False).head(10)

    # -------------------------------------------------
    # 6. LICENSE ANALYTICS
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy()
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).fillna(0)
        license_ai["license_risk"] = np.select(
            [license_ai["remaining"] <= 2, license_ai["usage_ratio"] > 0.9],
            ["🚨 Nguy cấp", "⚠️ Cảnh báo"], default="✅ Ổn định"
        )
        ai_metrics["license_alerts"] = int((license_ai["remaining"] <= 2).sum())

    # Cập nhật Summary
    ai_metrics["critical_assets"] = int((df_ai["risk_score"] >= 0.8).sum())
    ai_metrics["high_risk_assets"] = int((df_ai["risk_score"] >= 0.6).sum())
    
    if not maint_counts.empty and len(df_maint) > 0:
        mtbf = df_ai["age_days"].sum() / len(df_maint)
        ai_metrics["mtbf"] = f"{int(mtbf)} ngày"

    return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats
