import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - ENTERPRISE EDITION.
    Khả năng: Tự sửa lỗi dữ liệu (Self-healing), Phân tích đa chiều, Chống lệch mã (Merge Fix).
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    empty_df = pd.DataFrame(columns=['asset_tag', 'full_name', 'risk_level', 'branch', 'department'])
    df_ai_base, license_ai = empty_df.copy(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. HÀM CHỐNG LỆCH MÃ (FIX TRIỆT ĐỂ VẤN ĐỀ CỦA BẠN)
    # -------------------------------------------------
    def force_str_cleanup(series):
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True) # Xóa .0 nếu Pandas hiểu nhầm là float
            .str.strip()
            .replace(['nan', 'None', 'null', '<NA>', ''], pd.NA)
        )

    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()
    
    # Chuẩn hóa mã tài sản gán
    df_assets['assigned_to_code'] = force_str_cleanup(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. MERGE THÔNG MINH
    # -------------------------------------------------
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['employee_code'] = force_str_cleanup(df_staff['employee_code'])
        
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
    # 4. LOGIC PHÂN LOẠI "KHO TỔNG" VS "LỖI MÃ"
    # -------------------------------------------------
    # Case A: Thực sự là kho tổng (Mã trống)
    mask_in_stock = df_ai_base['assigned_to_code'].isna()
    df_ai_base.loc[mask_in_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_in_stock, 'department'] = 'Hạ tầng'
    df_ai_base.loc[mask_in_stock, 'branch'] = 'Toàn quốc'

    # Case B: Có mã nhưng không tìm thấy nhân viên (Lệch dữ liệu)
    mask_mismatch = df_ai_base['assigned_to_code'].notna() & df_ai_base['full_name'].isna()
    df_ai_base.loc[mask_mismatch, 'full_name'] = '⚠️ Mã ' + df_ai_base['assigned_to_code'].astype(str) + ' (Lỗi)'
    df_ai_base.loc[mask_mismatch, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_mismatch, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 5. XỬ LÝ THỜI GIAN & BẢO TRÌ
    # -------------------------------------------------
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # Tính số lần bảo trì từ JSON list
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
        lambda x: len(x) if isinstance(x, list) else (0 if pd.isna(x) else 1)
    )
    
    if df_maint is not None and not df_maint.empty:
        if "duration" in df_maint.columns:
            valid_dur = pd.to_numeric(df_maint["duration"], errors='coerce').dropna()
            if not valid_dur.empty:
                ai_metrics["mttr"] = f"{valid_dur.mean():.1f}h"
        
        avg_age = df_ai_base["age_days"].mean()
        avg_fails = df_ai_base['m_count'].mean()
        if avg_fails > 0:
            ai_metrics["mtbf"] = f"{int(avg_age / avg_fails)} ngày"

    # -------------------------------------------------
    # 6. MÔ HÌNH RỦI RO (RISK MATRIX)
    # -------------------------------------------------
    def get_spec_risk(spec_val):
        s = str(spec_val).lower()
        score = 0.5
        if any(x in s for x in ['i3', '4gb', 'hdd', '2010', '2012']): score += 0.3
        if any(x in s for x in ['i7', '16gb', '32gb', 'ssd', 'nvme']): score -= 0.3
        return np.clip(score, 0.1, 1.0)

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)
    
    # Weighting: 40% lỗi, 30% tuổi thọ, 30% cấu hình
    fail_factor = np.minimum(df_ai_base["m_count"] / 4, 1.0)
    age_factor = np.minimum(df_ai_base["age_days"] / (365 * 4), 1.0)
    
    df_ai_base["risk_score"] = (fail_factor * 0.4) + (age_factor * 0.3) + (df_ai_base['spec_score'] * 0.3)
    
    conds = [df_ai_base["risk_score"] >= 0.75, df_ai_base["risk_score"] >= 0.45]
    choices = ["🔴 Nguy cấp", "🟠 Cao"]
    df_ai_base["risk_level"] = np.select(conds, choices, default="🟢 Thấp")

    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_level"] == "🟠 Cao").sum())

    # -------------------------------------------------
    # 7. THỐNG KÊ (AGGREGATION)
    # -------------------------------------------------
    branch_stats = df_ai_base.groupby('branch').agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lỗi', 'risk_score': 'Rủi ro TB'}).reset_index()

    dept_stats = df_ai_base.groupby('department').agg({
        'asset_tag': 'count', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'risk_score': 'Rủi ro TB'}).reset_index()

    # 8. LICENSE ANALYTICS (Tối ưu hóa logic tính toán)
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy().rename(columns={'name': 'software_name'})
        for col in ['total_quantity', 'used_quantity', 'alert_threshold']:
            license_ai[col] = pd.to_numeric(license_ai[col], errors='coerce').fillna(0)
            
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = license_ai["used_quantity"] / license_ai["total_quantity"].replace(0, 1)
        
        l_conds = [
            license_ai["remaining"] <= license_ai["alert_threshold"],
            license_ai["usage_ratio"] >= 0.95
        ]
        l_choices = ["🚨 Sắp hết hạn mức", "⚠️ Sử dụng quá cao"]
        license_ai["license_risk"] = np.select(l_conds, l_choices, default="✅ Ổn định")
        ai_metrics["license_alerts"] = int((license_ai["license_risk"] != "✅ Ổn định").sum())

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
