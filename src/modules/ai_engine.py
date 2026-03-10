import pandas as pd
import numpy as np
import json

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - Tối ưu cho dữ liệu thực tế Supabase.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    df_ai_base, license_ai = pd.DataFrame(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU & AI MAPPING (STAFF & ASSETS)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Nối với bảng Staff để lấy Full Name, Department và Branch thực tế
    if df_staff is not None and not df_staff.empty:
        df_ai_base = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )
        df_ai_base['full_name'] = df_ai_base['full_name'].fillna("Kho tổng / Hệ thống")
        df_ai_base['department'] = df_ai_base['department'].fillna("Hạ tầng")
        df_ai_base['branch'] = df_ai_base['branch'].fillna(df_ai_base['asset_tag'].str.split('-').str[-1])
    else:
        df_ai_base = df_assets.copy()
        df_ai_base['full_name'] = df_ai_base['assigned_to_code'].fillna("Kho tổng")
        df_ai_base['branch'] = df_ai_base['asset_tag'].str.split('-').str[-1]
        df_ai_base['department'] = "Khối Văn phòng"

    # Xử lý thời gian
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR)
    # -------------------------------------------------
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    if df_maint is not None and not df_maint.empty:
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        if "duration" in df_maint.columns:
            ai_metrics["mttr"] = f"{df_maint['duration'].median():.1f} giờ"

    # -------------------------------------------------
    # 4. MÔ HÌNH RỦI RO (RISK MODEL)
    # -------------------------------------------------
    def get_spec_risk(spec_str):
        try:
            if not spec_str: return 0.5
            s = str(spec_str).lower()
            if 'i3' in s or '4gb' in s: return 0.9
            if 'i7' in s or '16gb' in s or '32gb' in s: return 0.2
            return 0.5
        except: return 0.5

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)
    fail_f = np.minimum(df_ai_base["m_count"] / 3, 1)
    age_f = np.minimum(df_ai_base["age_days"] / (365 * 3), 1)
    
    df_ai_base["risk_score"] = (0.4 * fail_f + 0.3 * age_f + 0.3 * df_ai_base['spec_score'])
    df_ai_base["risk_level"] = np.select(
        [df_ai_base["risk_score"] >= 0.7, df_ai_base["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp"
    )

    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_level"] == "🟠 Cao").sum())

    # -------------------------------------------------
    # 5. THỐNG KÊ CHI TIẾT
    # -------------------------------------------------
    branch_stats = df_ai_base.groupby('branch').agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro TB'}).reset_index()

    user_stats = df_ai_base.groupby(['assigned_to_code', 'full_name', 'department', 'branch']).agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Máy giữ', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro Max'}).reset_index()
    user_stats = user_stats.sort_values('Rủi ro Max', ascending=False).head(10)

    # -------------------------------------------------
    # 6. LICENSE ANALYTICS
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy().rename(columns={'name': 'software_name'})
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).replace([np.inf, -np.inf], 0).fillna(0)
        
        license_ai["license_risk"] = np.select(
            [license_ai["remaining"] <= license_ai["alert_threshold"], license_ai["usage_ratio"] >= 0.9],
            ["🚨 Sắp hết hạn mức", "⚠️ Sử dụng cao"], default="✅ Ổn định"
        )
        ai_metrics["license_alerts"] = int((license_ai["license_risk"] != "✅ Ổn định").sum())

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
