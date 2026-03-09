import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    # 1. Khởi tạo giá trị mặc định (Apple Design Standard)
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    
    # Khởi tạo các DataFrame rỗng để an toàn khi return
    df_ai, license_ai = pd.DataFrame(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    # Sử dụng dấu gạch dưới (_) để bỏ qua các giá trị dư thừa
    metrics, df_ai, lic_ai, *others = calculate_ai_metrics(df_assets, df_maint, df_lic)
    if df_assets.empty:
        return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU TÀI SẢN (ALIGNED WITH YOUR DB)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Đồng bộ cột assigned_to_code từ bảng dữ liệu thực tế của bạn
    if 'assigned_to_code' in df_assets.columns:
        df_assets['assigned_to'] = df_assets['assigned_to_code'].fillna("Kho tổng")
    else:
        df_assets['assigned_to'] = "Chưa xác định"

    # AI Heuristics: Tự động phân loại nếu DB thiếu cột
    # Tách chi nhánh: PC0001-HCM -> HCM, PC0001-MB -> MB
    df_assets['branch'] = df_assets['asset_tag'].str.split('-').str[-1].fillna("Khác")
    
    # Suy luận phòng ban dựa trên loại máy (type)
    if 'department' not in df_assets.columns:
        df_assets['department'] = df_assets['type'].apply(
            lambda x: "Hạ tầng Server" if x == 'server' else "Khối Văn phòng"
        )

    df_assets["created_at"] = pd.to_datetime(df_assets["created_at"], errors="coerce", utc=True).fillna(now)
    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH LỊCH SỬ BẢO TRÌ (MTBF/MTTR)
    # -------------------------------------------------
    if not df_maint.empty:
        df_maint = df_maint.copy()
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        maint_counts = df_maint.groupby("asset_tag").size().reset_index(name="m_count")
        last_fail = df_maint.groupby("asset_tag")["performed_at"].max().reset_index(name="last_failure")
        
        if "duration" in df_maint.columns:
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

    # Risk Scoring Model
    age_f = np.minimum(df_ai["age_days"] / 1095, 1)      # Max rủi ro sau 3 năm
    fail_f = np.minimum(df_ai["m_count"] / 5, 1)        # Max rủi ro sau 5 lần hỏng
    rec_f = np.maximum(0, 1 - df_ai["days_since_failure"] / 365) # Hỏng trong 1 năm qua

    df_ai["risk_score"] = (0.4 * fail_f + 0.4 * age_f + 0.2 * rec_f)
    # Sigmoid function để làm mượt xác suất hỏng hóc
    df_ai["failure_prob"] = 1 / (1 + np.exp(-6 * (df_ai["risk_score"] - 0.5)))
    
    df_ai["risk_level"] = np.select(
        [df_ai["risk_score"] >= 0.8, df_ai["risk_score"] >= 0.6, df_ai["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao", "🟡 Trung bình"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 5. ĐỊNH DANH THỐNG KÊ (BRANCH / DEPT / USER)
    # -------------------------------------------------
    # 1. Chi nhánh (HCM/MB/DN)
    branch_stats = df_ai.groupby('branch').agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Lượt sửa', 'risk_score': 'Rủi ro TB'})

    # 2. Phòng ban (Tự động hóa)
    dept_stats = df_ai.groupby('department').agg({
        'm_count': 'sum', 'failure_prob': 'mean'
    }).sort_values('m_count', ascending=False)

    # 3. Người dùng (Dựa trên assigned_to_code của bạn)
    user_stats = df_ai.groupby(['assigned_to', 'department']).agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Số thiết bị', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro Max'})
    user_stats = user_stats.sort_values('Tổng lượt hỏng', ascending=False).head(10)

    # -------------------------------------------------
    # 6. PHÂN TÍCH RỦI RO BẢN QUYỀN (LICENSE)
    # -------------------------------------------------
    if not df_lic.empty:
        license_ai = df_lic.copy()
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).fillna(0)
        
        license_ai["license_risk"] = np.select(
            [license_ai["remaining"] <= 2, license_ai["usage_ratio"] > 0.9],
            ["🚨 Nguy cấp", "⚠️ Cảnh báo"], default="✅ Ổn định"
        )
        ai_metrics["license_alerts"] = int((license_ai["remaining"] <= 2).sum())

    # Cập nhật Summary Metrics cuối cùng
    ai_metrics["critical_assets"] = int((df_ai["risk_score"] >= 0.8).sum())
    ai_metrics["high_risk_assets"] = int((df_ai["risk_score"] >= 0.6).sum())
    
    if not df_maint.empty and df_maint.shape[0] > 0:
        mtbf = df_ai["age_days"].sum() / df_maint.shape[0]
        ai_metrics["mtbf"] = f"{int(mtbf)} ngày"

    return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats
