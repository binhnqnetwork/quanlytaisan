import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):
    # 1. Khởi tạo cấu trúc trả về
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_assets = df_assets.copy()

    # 2. HÀM CHUẨN HÓA CƯỠNG CHẾ
    def clean_key(series):
        if series is None: return pd.Series(dtype="object")
        return (
            series.astype(str)
            .str.replace(r'\.0$', '', regex=True)
            .str.strip()
            .replace(['nan', 'None', '<NA>', ''], np.nan)
        )

    # 3. CHUẨN HÓA KHÓA & MERGE (Giữ nguyên logic gốc)
    df_assets['link_key'] = clean_key(df_assets['assigned_to_code'])
    
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['staff_key'] = clean_key(df_staff['employee_code'])
        staff_lookup = df_staff[['staff_key', 'full_name', 'department', 'branch']].drop_duplicates('staff_key')
        df_final = pd.merge(df_assets, staff_lookup, left_on='link_key', right_on='staff_key', how='left')
    else:
        df_final = df_assets.copy()
        df_final['full_name'] = np.nan

    # 4. XỬ LÝ LOGIC HIỂN THỊ (Giữ nguyên logic gốc)
    is_empty_code = df_final['link_key'].isna()
    df_final.loc[is_empty_code, 'full_name'] = "📦 Kho tổng / Hệ thống"
    df_final.loc[is_empty_code, 'department'] = df_final.loc[is_empty_code, 'department'].fillna("Hạ tầng")
    df_final.loc[is_empty_code, 'branch'] = "Toàn quốc"

    mask_error = (~is_empty_code) & (df_final['full_name'].isna())
    df_final.loc[mask_error, 'full_name'] = "⚠️ Lỗi: Mã " + df_final['assigned_to_code'].astype(str)
    df_final.loc[mask_error, 'department'] = "Cần rà soát"
    df_final.loc[mask_error, 'branch'] = "Chưa xác định"

    # 5. TẠO CÁC BẢNG THỐNG KÊ (Đã sửa đổi để gộp dòng theo nhân viên)
    df_final['risk_level'] = "🟢 Thấp"
    
    # Tạo bảng Drill-down Detail: Gộp tài sản theo nhân viên
    # Thay vì để mỗi máy 1 dòng, ta gộp lại theo Người sở hữu
    df_drill_down = df_final.groupby(['full_name', 'department', 'branch', 'risk_level']).agg({
        'asset_tag': lambda x: " | ".join(x.astype(str)),
        'id': 'count' # Dùng để đếm số lượng tài sản
    }).reset_index()
    
    # Đổi tên cột để hiển thị chuẩn Pro
    df_drill_down = df_drill_down.rename(columns={
        'full_name': 'Nhân viên sở hữu',
        'asset_tag': 'Mã máy',
        'id': 'Số lượng'
    })

    # Các bảng thống kê phụ khác
    branch_stats = df_final.groupby('branch').size().reset_index(name='asset_count')
    dept_stats = df_final.groupby('department').size().reset_index(name='asset_count')
    user_stats = df_final.groupby('full_name').size().reset_index(name='assets').sort_values('assets', ascending=False)

    # Trả về df_drill_down ở vị trí dataframe thứ 2 (df_final cũ)
    return ai_metrics, df_drill_down, pd.DataFrame(), branch_stats, dept_stats, user_stats
