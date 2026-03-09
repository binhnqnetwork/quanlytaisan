import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    # 1. Khởi tạo giá trị mặc định
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    
    # Khởi tạo các DataFrame rỗng để tránh lỗi trả về
    df_ai = pd.DataFrame()
    license_ai = pd.DataFrame()
    branch_stats = pd.DataFrame()
    dept_stats = pd.DataFrame()
    user_stats = pd.DataFrame()

    if df_assets.empty:
        return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU TÀI SẢN
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Xử lý các cột định danh quan trọng
    required_cols = ['department', 'assigned_to', 'status', 'last_maintenance']
    for col in required_cols:
        df_assets[col] = df_assets[col].fillna("Chưa xác định")

    df_assets["created_at"] = pd.to_datetime(df_assets["created_at"], errors="coerce", utc=True).fillna(now)
    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days
    
    # Tách chi nhánh từ asset_tag (VD: SV001-HCM -> HCM)
    df_assets['branch'] = df_assets['asset_tag'].str.split('-').str[-1].fillna("Khác")

    # -------------------------------------------------
    # 3. PHÂN TÍCH LỊCH SỬ BẢO TRÌ (MTBF/MTTR)
    # -------------------------------------------------
    if not df_maint.empty:
        df_maint = df_maint.copy()
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)

        maint_counts = df_maint.groupby("asset_tag").size().reset_index(name="m_count")
        last_fail = df_maint.groupby("asset_tag")["performed_at"].max().reset_index(name="last_failure")

        if "duration" in df_maint.columns:
            # Tính trung vị thời gian sửa chữa
            mttr = df_maint["duration"].median()
            ai_metrics["mttr"] = f"{mttr:.1f} hrs"
    else:
        maint_counts = pd.DataFrame(columns=["asset_tag", "m_count"])
        last_fail = pd.DataFrame(columns=["asset_tag", "last_failure"])

    # -------------------------------------------------
    # 4. MÔ HÌNH DỰ BÁO RỦI RO (AI RISK MODEL)
    # -------------------------------------------------
    df_ai = pd.merge(df_assets, maint_counts, on="asset_tag", how="left")
    df_ai = pd.merge(df_ai, last_fail, on="asset_tag", how="left")

    df_ai["m_count"] = df_ai["m_count"].fillna(0)
    df_ai["days_since_failure"] = (now - pd.to_datetime(df_ai["last_failure"], utc=True)).dt.days.fillna(9999)

    # Risk factors (Trọng số 40-40-20)
    age_f = np.minimum(df_ai["age_days"] / 1095, 1)      # Max rủi ro sau 3 năm
    fail_f = np.minimum(df_ai["m_count"] / 5, 1)        # Max rủi ro sau 5 lần hỏng
    rec_f = np.maximum(0, 1 - df_ai["days_since_failure"] / 365) # Hỏng gần đây

    df_ai["risk_score"] = (0.4 * fail_f + 0.4 * age_f + 0.2 * rec_f)
    df_ai["failure_prob"] = 1 / (1 + np.exp(-6 * (df_ai["risk_score"] - 0.5))) # Sigmoid
    
    # Phân loại rủi ro theo màu sắc
    df_ai["risk_level"] = np.select(
        [df_ai["risk_score"] >= 0.8, df_ai["risk_score"] >= 0.6, df_ai["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao", "🟡 Trung bình"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 5. THỐNG KÊ THEO CHI NHÁNH, PHÒNG BAN & NGƯỜI DÙNG
    # -------------------------------------------------
    # Chi nhánh
    branch_stats = df_ai.groupby('branch').agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Lượt sửa', 'risk_score': 'Rủi ro TB'})

    # Phòng ban
    dept_stats = df_ai.groupby('department').agg({
        'm_count': 'sum', 'risk_score': 'max'
    }).sort_values('m_count', ascending=False)

    # Người dùng (Top 10 người dùng cần lưu ý)
    user_stats = df_ai.groupby(['assigned_to', 'department']).agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Máy giữ', 'm_count': 'Lượt hỏng', 'risk_score': 'Rủi ro max'})
    user_stats = user_stats.sort_values('Lượt hỏng', ascending=False).head(10)

    # -------------------------------------------------
    # 6. PHÂN TÍCH RỦI RO BẢN QUYỀN (LICENSE)
    # -------------------------------------------------
    if not df_lic.empty:
        license_ai = df_lic.copy()
        # Tính toán trực tiếp để tránh lỗi missing column 'remaining_qty'
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).fillna(0)
        
        license_ai["license_risk"] = np.select(
            [license_ai["remaining"] <= 2, license_ai["usage_ratio"] > 0.9],
            ["🚨 Nguy cấp", "⚠️ Cảnh báo"], default="✅ Ổn định"
        )
        ai_metrics["license_alerts"] = int((license_ai["remaining"] <= 2).sum())

    # Cập nhật Summary Metrics
    ai_metrics["critical_assets"] = int((df_ai["risk_score"] >= 0.8).sum())
    ai_metrics["high_risk_assets"] = int((df_ai["risk_score"] >= 0.6).sum())
    
    if not df_maint.empty and df_maint.shape[0] > 0:
        mtbf = df_ai["age_days"].sum() / df_maint.shape[0]
        ai_metrics["mtbf"] = f"{int(mtbf)} ngày"

    return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats
