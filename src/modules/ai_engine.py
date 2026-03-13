import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    # -------------------------------------------------
    # 1. KHỞI TẠO
    # -------------------------------------------------
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    df_ai_base = pd.DataFrame()
    license_ai = pd.DataFrame()
    branch_stats = pd.DataFrame()
    dept_stats = pd.DataFrame()
    user_stats = pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. HÀM LÀM SẠCH "BÊ TÔNG" (ÉP KHỚP MỌI GIÁ)
    # -------------------------------------------------
    def hard_clean(series):
        return (
            series.astype(str)
            .str.split('.').str[0] # Xóa phần thập phân .0 nếu có
            .str.extract('(\d+)', expand=False) # Chỉ giữ lại các con số
            .str.strip()
            .replace(['nan', 'None', 'null', ''], np.nan)
        )

    df_assets = df_assets.copy()
    # Tạo mã sạch để merge
    df_assets['clean_join_code'] = hard_clean(df_assets['assigned_to_code'])

    # -------------------------------------------------
    # 3. XỬ LÝ STAFF TỪ SUPABASE (FIX LỖI IMAGE_C9EFDE)
    # -------------------------------------------------
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        # Ép mã nhân viên Supabase về cùng định dạng sạch
        df_staff['clean_staff_code'] = hard_clean(df_staff['employee_code'])
        
        # Loại bỏ trùng lặp để tránh làm tăng số lượng máy khi merge
        staff_lookup = df_staff[['clean_staff_code', 'full_name', 'department', 'branch']].drop_duplicates('clean_staff_code')

        # Thực hiện Merge
        df_ai_base = pd.merge(
            df_assets,
            staff_lookup,
            left_on='clean_join_code',
            right_on='clean_staff_code',
            how='left'
        )
    else:
        df_ai_base = df_assets.copy()

    # Đảm bảo cột luôn tồn tại để không lỗi dashboard
    for col in ['full_name', 'department', 'branch']:
        if col not in df_ai_base.columns:
            df_ai_base[col] = np.nan

    # -------------------------------------------------
    # 4. LOGIC PHÂN LOẠI (IMAGE_CB41D9 FIX)
    # -------------------------------------------------
    # Ưu tiên: Nếu merge thành công -> dùng dữ liệu Staff. 
    # Nếu thất bại -> Kiểm tra xem có phải kho không, nếu không mới báo Lỗi.

    mask_has_code = df_ai_base['clean_join_code'].notna()
    mask_no_name = df_ai_base['full_name'].isna()

    # TRƯỜNG HỢP KHO (Không có mã)
    mask_stock = ~mask_has_code
    df_ai_base.loc[mask_stock, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[mask_stock, 'department'] = df_ai_base.loc[mask_stock, 'department'].fillna('Lưu kho')
    df_ai_base.loc[mask_stock, 'branch'] = df_ai_base.loc[mask_stock, 'branch'].fillna('Toàn quốc')

    # TRƯỜNG HỢP LỖI (Có mã nhưng tìm không thấy trong Staff)
    mask_error = mask_has_code & mask_no_name
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # -------------------------------------------------
    # 5. THỜI GIAN & RỦI RO (FIXED TZ)
    # -------------------------------------------------
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base['created_at'] = pd.to_datetime(df_ai_base.get('created_at', now), errors="coerce", utc=True).fillna(now)
    df_ai_base['age_days'] = (now - df_ai_base['created_at']).dt.days

    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(lambda x: len(x) if isinstance(x, list) else 0) if 'maintenance_history' in df_ai_base.columns else 0

    def get_spec_risk(s):
        s = str(s).lower()
        score = 0.5
        if any(x in s for x in ['i3', '4gb', 'hdd']): score += 0.3
        if any(x in s for x in ['i7', '16gb', 'ssd', 'nvme']): score -= 0.3
        return np.clip(score, 0.1, 1.0)

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk) if 'specs' in df_ai_base.columns else 0.5
    
    # Tính Risk Score
    df_ai_base["risk_score"] = (np.minimum(df_ai_base["m_count"] / 4, 1.0) * 0.4) + \
                               (np.minimum(df_ai_base["age_days"] / 1460, 1.0) * 0.3) + \
                               (df_ai_base['spec_score'] * 0.3)
    
    df_ai_base["risk_level"] = np.select(
        [df_ai_base["risk_score"] >= 0.75, df_ai_base["risk_score"] >= 0.45],
        ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 6. KPI & TRẢ KẾT QUẢ
    # -------------------------------------------------
    ai_metrics["critical_assets"] = int((df_ai_base["risk_level"] == "🔴 Nguy cấp").sum())
    ai_metrics["high_risk_assets"] = int((df_ai_base["risk_level"] == "🟠 Cao").sum())

    if df_lic is not None and not df_lic.empty:
        df_lic['expiry_date'] = pd.to_datetime(df_lic['expiry_date'], errors='coerce', utc=True)
        license_ai = df_lic.assign(days_left=(df_lic['expiry_date'] - now).dt.days)
        ai_metrics["license_alerts"] = int((license_ai['days_left'] < 30).sum())
    else:
        license_ai = pd.DataFrame()

    branch_stats = df_ai_base.groupby('branch', dropna=False).agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    dept_stats = df_ai_base.groupby('department', dropna=False).agg(asset_count=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).reset_index()
    user_stats = df_ai_base.groupby('full_name', dropna=False).agg(assets=('asset_tag', 'count'), avg_risk=('risk_score', 'mean')).sort_values("assets", ascending=False).reset_index()

    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
