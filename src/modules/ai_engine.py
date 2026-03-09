import pandas as pd
import numpy as np
import json

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    """
    Hệ thống phân tích tài sản thông minh - Tối ưu cho dữ liệu thực tế Supabase.
    Trả về 6 giá trị: metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    df_ai, license_ai = pd.DataFrame(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU & AI HEURISTICS
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Xử lý assigned_to từ code thực tế (ví dụ: 3140, 10438)
    df_assets['assigned_to'] = df_assets['assigned_to_code'].fillna("Kho tổng") if 'assigned_to_code' in df_assets.columns else "Chưa xác định"

    # AI Suy luận Chi nhánh và Phòng ban
    df_assets['branch'] = df_assets['asset_tag'].str.split('-').str[-1].fillna("Khác")
    if 'department' not in df_assets.columns:
        df_assets['department'] = df_assets['type'].apply(lambda x: "Hạ tầng Server" if str(x).lower() == 'server' else "Khối Văn phòng")

    # Xử lý thời gian
    df_assets["created_at"] = pd.to_datetime(df_assets["created_at"], errors="coerce", utc=True).fillna(now)
    df_assets["age_days"] = (now - df_assets["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR)
    # -------------------------------------------------
    maint_counts = pd.DataFrame(columns=["asset_tag", "m_count"])
    last_fail = pd.DataFrame(columns=["asset_tag", "last_failure"])

    if df_maint is not None and not df_maint.empty:
        df_maint = df_maint.copy()
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        maint_counts = df_maint.groupby("asset_tag").size().reset_index(name="m_count")
        last_fail = df_maint.groupby("asset_tag")["performed_at"].max().reset_index(name="last_failure")
        
        if "duration" in df_maint.columns:
            ai_metrics["mttr"] = f"{df_maint['duration'].median():.1f} hrs"

    # -------------------------------------------------
    # 4. MÔ HÌNH RỦI RO CHIÊN SÂU (ADVANCED RISK MODEL)
    # -------------------------------------------------
    df_ai = pd.merge(df_assets, maint_counts, on="asset_tag", how="left")
    df_ai = pd.merge(df_ai, last_fail, on="asset_tag", how="left")
    df_ai["m_count"] = df_ai["m_count"].fillna(0)
    df_ai["days_since_failure"] = (now - pd.to_datetime(df_ai["last_failure"], utc=True)).dt.days.fillna(9999)

    # NÂNG CẤP: Phân tích cấu hình từ JSON specs để tính điểm rủi ro cấu hình thấp
    def get_spec_risk(spec_str):
        try:
            if not spec_str or spec_str == 'None': return 0.5
            s = str(spec_str).lower()
            if 'i3' in s or '4gb' in s: return 0.8  # Máy yếu rủi ro cao
            if 'i7' in s or '32gb' in s: return 0.2 # Máy mạnh rủi ro thấp
            return 0.4
        except: return 0.5

    df_ai['spec_score'] = df_ai['specs'].apply(get_spec_risk)

    # Risk Weighting: 30% Lịch sử hỏng - 30% Tuổi thọ - 20% Gần đây - 20% Cấu hình
    age_f = np.minimum(df_ai["age_days"] / 1095, 1)
    fail_f = np.minimum(df_ai["m_count"] / 5, 1)
    rec_f = np.maximum(0, 1 - df_ai["days_since_failure"] / 365)
    
    df_ai["risk_score"] = (0.3 * fail_f + 0.3 * age_f + 0.2 * rec_f + 0.2 * df_ai['spec_score'])
    df_ai["failure_prob"] = 1 / (1 + np.exp(-6 * (df_ai["risk_score"] - 0.5)))
    
    df_ai["risk_level"] = np.select(
        [df_ai["risk_score"] >= 0.75, df_ai["risk_score"] >= 0.5, df_ai["risk_score"] >= 0.3],
        ["🔴 Nguy cấp", "🟠 Cao", "🟡 Trung bình"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # -------------------------------------------------
    # 5. THỐNG KÊ CHI TIẾT (BRANCH / USER) - ĐỒNG BỘ TÊN CỘT
    # -------------------------------------------------
    # Thống kê chi nhánh
    branch_stats = df_ai.groupby('branch').agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro TB'})

    # Thống kê người dùng (User) - ĐÂY LÀ NƠI GÂY LỖI
    user_stats = df_ai.groupby(['assigned_to', 'department']).agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Máy giữ', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro Max'})
    
    # Sắp xếp theo 'Tổng lượt hỏng' vừa đổi tên
    user_stats = user_stats.sort_values('Tổng lượt hỏng', ascending=False).head(10)
    # 6. LICENSE ANALYTICS & SUMMARY
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

    ai_metrics["critical_assets"] = int((df_ai["risk_score"] >= 0.75).sum())
    ai_metrics["high_risk_assets"] = int((df_ai["risk_score"] >= 0.5).sum())
    
    if df_maint is not None and len(df_maint) > 0:
        mtbf = df_ai["age_days"].sum() / len(df_maint)
        ai_metrics["mtbf"] = f"{int(mtbf)} ngày"

    return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats
