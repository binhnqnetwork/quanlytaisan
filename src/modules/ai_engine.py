import pandas as pd
import numpy as np
import json

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - Tối ưu cho dữ liệu thực tế Supabase.
    Bổ sung df_staff để mapping Tên nhân viên và Chi nhánh chính xác.
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
        # Xử lý trường hợp máy trong kho (không có nhân viên)
        df_ai_base['full_name'] = df_ai_base['full_name'].fillna("Kho tổng / Hệ thống")
        df_ai_base['department'] = df_ai_base['department'].fillna("Hạ tầng")
        df_ai_base['branch'] = df_ai_base['branch'].fillna(df_ai_base['asset_tag'].str.split('-').str[-1])
    else:
        # Fallback nếu không có bảng staff
        df_ai_base = df_assets.copy()
        df_ai_base['full_name'] = df_ai_base['assigned_to_code'].fillna("Kho tổng")
        df_ai_base['branch'] = df_ai_base['asset_tag'].str.split('-').str[-1]
        if 'department' not in df_ai_base.columns:
            df_ai_base['department'] = "Khối Văn phòng"

    # Xử lý thời gian
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR) - Đếm từ maintenance_history
    # -------------------------------------------------
    # Thay vì dùng bảng df_maint riêng, ta đếm trực tiếp từ cột maintenance_history (list) của assets
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    # Tính MTTR giả định nếu có dữ liệu trong m_history (hoặc dùng df_maint nếu có)
    if df_maint is not None and not df_maint.empty:
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        if "duration" in df_maint.columns:
            ai_metrics["mttr"] = f"{df_maint['duration'].median():.1f} giờ"

    # -------------------------------------------------
    # 4. MÔ HÌNH RỦI RO CHUYÊN SÂU (ADVANCED RISK MODEL)
    # -------------------------------------------------
    def get_spec_risk(spec_str):
        try:
            if not spec_str: return 0.5
            s = str(spec_str).lower()
            if 'i3' in s or '4gb' in s: return 0.9  # Rủi ro rất cao vì dễ treo máy
            if 'i7' in s or '16gb' in s or '32gb' in s: return 0.2
            return 0.5
        except: return 0.5

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)

    # Trọng số rủi ro: 40% Lịch sử hỏng - 30% Tuổi thọ - 30% Cấu hình
    fail_f = np.minimum(df_ai_base["m_count"] / 3, 1) # 3 lần hỏng là max risk
    age_f = np.minimum(df_ai_base["age_days"] / (365 * 3), 1) # 3 năm là máy cũ
    
    df_ai_base["risk_score"] = (0.4 * fail_f + 0.3 * age_f + 0.3 * df_ai_base['spec_score'])
    
    df_ai_base["risk_level"] = np.select(
        [df_ai_base["risk_score"] >= 0.7, df_ai_base["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 5. THỐNG KÊ CHI TIẾT (BRANCH / USER)
    # -------------------------------------------------
    # Thống kê chi nhánh
    branch_stats = df_ai_base.groupby('branch').agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro TB'}).reset_index()

    # Thống kê người dùng (Top 10 rủi ro)
    user_stats = df_ai_base.groupby(['assigned_to_code', 'full_name', 'department', 'branch']).agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Máy giữ', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro Max'}).reset_index()
    
    user_stats = user_stats.sort_values('Tổng lượt hỏng', ascending=False).head(10)

    # -------------------------------------------------
    # 6. LICENSE ANALYTICS
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy()
        # Tính toán dựa trên cột thực tế của bạn (software_name, total_quantity, used_quantity)
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).replace([np.inf, -np.inf], 0).fillna(0)
        
        license_ai["license_risk"] = np.select(
            [license_ai["remaining"] <= 1, license_ai["usage_ratio"] >= 1.0],
            ["🚨 Nguy cấp", "⚠️ Hết hạn mức"], default="✅ Ổn định"
        )
        ai_metrics["license_alerts"] = int((license_ai["remaining"] <= 1).sum())

    # Summary Metrics
    ai_metrics["critical_assets"] = int((df_ai_base["risk_score"] >= 0.7).sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_score"] >= 0.4).sum())
    
    if df_maint is not None and len(df_maint) > 0:
        mtbf = df_ai_base["age_days"].sum() / (len(df_maint) + 1)
        ai_metrics["mtbf"] = f"{int(mtbf)} ngày"

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
