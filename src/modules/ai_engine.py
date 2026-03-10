import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - ENTERPRISE EDITION.
    Khả năng: Tự sửa lỗi dữ liệu (Self-healing), Phân tích đa chiều, Chống crash.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH & KIỂM TRA ĐẦU VÀO
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    # Khởi tạo DataFrame rỗng với các cột dự phòng để tránh lỗi hiển thị ở Dashboard
    empty_df = pd.DataFrame(columns=['asset_tag', 'full_name', 'risk_level', 'branch', 'department'])
    df_ai_base, license_ai = empty_df.copy(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU & MAPPING (CHỐNG LỖI KEYERROR)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Xử lý Mã nhân viên: Ép về string, xóa khoảng trắng, xử lý 'null' (CỰC KỲ QUAN TRỌNG)
    df_assets['assigned_to_code'] = df_assets['assigned_to_code'].astype(str).str.strip().replace(['None', 'nan', '<NA>'], '')

    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['employee_code'] = df_staff['employee_code'].astype(str).str.strip()
        
        # Loại bỏ các cột trùng lặp nếu có trước khi merge
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

    # ĐẢM BẢO CỘT TỒN TẠI (Self-healing logic)
    needed_cols = {'full_name': 'Kho tổng / Hệ thống', 'department': 'Hạ tầng', 'branch': 'Toàn quốc'}
    for col, default_val in needed_cols.items():
        if col not in df_ai_base.columns:
            df_ai_base[col] = default_val
        df_ai_base[col] = df_ai_base[col].fillna(default_val)

    # Xử lý thời gian
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR) - CHUẨN PRO
    # -------------------------------------------------
    # Tính toán lượt hỏng dựa trên lịch sử (JSON list)
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(
        lambda x: len(x) if isinstance(x, list) else (0 if pd.isna(x) else 1)
    )
    
    if df_maint is not None and not df_maint.empty:
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        # MTTR: Thời gian sửa chữa trung bình (nếu có cột duration)
        if "duration" in df_maint.columns:
            valid_duration = pd.to_numeric(df_maint["duration"], errors='coerce').dropna()
            if not valid_duration.empty:
                ai_metrics["mttr"] = f"{valid_duration.mean():.1f}h"
        
        # MTBF (Ước tính): Tuổi đời thiết bị / số lần hỏng
        avg_age = df_ai_base["age_days"].mean()
        avg_fails = df_ai_base['m_count'].mean()
        if avg_fails > 0:
            ai_metrics["mtbf"] = f"{int(avg_age / avg_fails)} ngày"

    # -------------------------------------------------
    # 4. MÔ HÌNH RỦI RO ĐA BIẾN (RISK MATRIX)
    # -------------------------------------------------
    def get_spec_risk(spec_val):
        """Phân tích cấu hình phần cứng nhúng"""
        s = str(spec_val).lower()
        score = 0.5 # Mặc định trung bình
        if any(x in s for x in ['i3', '4gb', 'hdd', '2010', '2012']): score += 0.3
        if any(x in s for x in ['i7', '16gb', '32gb', 'ssd', 'nvme']): score -= 0.3
        return np.clip(score, 0.1, 1.0)

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)
    
    # Tính điểm Risk tổng hợp (Weighting)
    fail_factor = np.minimum(df_ai_base["m_count"] / 4, 1.0) # 4 lần hỏng là max rủi ro
    age_factor = np.minimum(df_ai_base["age_days"] / (365 * 4), 1.0) # 4 năm là khấu hao hết
    
    df_ai_base["risk_score"] = (fail_factor * 0.4) + (age_factor * 0.3) + (df_ai_base['spec_score'] * 0.3)
    
    # Phân cấp rủi ro
    conditions = [df_ai_base["risk_score"] >= 0.75, df_ai_base["risk_score"] >= 0.45]
    choices = ["🔴 Nguy cấp", "🟠 Cao"]
    df_ai_base["risk_level"] = np.select(conditions, choices, default="🟢 Thấp")

    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_level"] == "🟠 Cao").sum())

    # -------------------------------------------------
    # 5. THỐNG KÊ CHI NHÁNH & PHÒNG BAN
    # -------------------------------------------------
    branch_stats = df_ai_base.groupby('branch').agg({
        'asset_tag': 'count', 'm_count': 'sum', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lỗi', 'risk_score': 'Rủi ro TB'}).reset_index()

    dept_stats = df_ai_base.groupby('department').agg({
        'asset_tag': 'count', 'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'risk_score': 'Rủi ro TB'}).reset_index()

    # -------------------------------------------------
    # 6. LICENSE ANALYTICS
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy().rename(columns={'name': 'software_name'})
        # Đảm bảo số lượng là kiểu số
        for col in ['total_quantity', 'used_quantity', 'alert_threshold']:
            license_ai[col] = pd.to_numeric(license_ai[col], errors='coerce').fillna(0)
            
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        license_ai["usage_ratio"] = license_ai["used_quantity"] / license_ai.apply(lambda x: max(x["total_quantity"], 1), axis=1)
        
        l_conditions = [
            license_ai["remaining"] <= license_ai["alert_threshold"],
            license_ai["usage_ratio"] >= 0.95
        ]
        l_choices = ["🚨 Sắp hết hạn mức", "⚠️ Sử dụng quá cao"]
        license_ai["license_risk"] = np.select(l_conditions, l_choices, default="✅ Ổn định")
        ai_metrics["license_alerts"] = int((license_ai["license_risk"] != "✅ Ổn định").sum())

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
