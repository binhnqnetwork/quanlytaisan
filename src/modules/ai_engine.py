import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):
    # 1. Khởi tạo cấu trúc trả về
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_assets = df_assets.copy()

    # 2. HÀM CHUẨN HÓA CƯỠNG CHẾ (APPLE STYLE: SIMPLICITY & PRECISION)
    def clean_key(series):
        if series is None: return pd.Series(dtype="object")
        return (
            series.astype(str)                  # Ép tất cả về chuỗi
            .str.replace(r'\.0$', '', regex=True) # Xóa đuôi số thập phân .0
            .str.strip()                        # Xóa khoảng trắng thừa
            .replace(['nan', 'None', '<NA>', ''], np.nan)
        )

    # 3. CHUẨN HÓA KHÓA Ở CẢ HAI BẢNG TRƯỚC KHI MERGE
    df_assets['link_key'] = clean_key(df_assets['assigned_to_code'])
    
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['staff_key'] = clean_key(df_staff['employee_code'])
        
        # Tạo bảng tra cứu nhân viên sạch (không trùng lặp)
        staff_lookup = df_staff[['staff_key', 'full_name', 'department', 'branch']].drop_duplicates('staff_key')
        
        # THỰC HIỆN KẾT NỐI (MERGE)
        df_final = pd.merge(df_assets, staff_lookup, left_on='link_key', right_on='staff_key', how='left')
    else:
        df_final = df_assets.copy()
        df_final['full_name'] = np.nan

    # 4. XỬ LÝ LOGIC HIỂN THỊ (THE FINAL POLISH)
    # Xác định dòng nào thực sự trống mã (như PC0001-HCM)
    is_empty_code = df_final['link_key'].isna()

    # Nhánh 1: Xử lý Máy Kho (Mã rỗng)
    df_final.loc[is_empty_code, 'full_name'] = "📦 Kho tổng / Hệ thống"
    df_final.loc[is_empty_code, 'department'] = df_final.loc[is_empty_code, 'department'].fillna("Hạ tầng") # Giữ lại "Hạ tầng"
    df_final.loc[is_empty_code, 'branch'] = "Toàn quốc"

    # Nhánh 2: Xử lý Lỗi (Có mã nhưng Merge thất bại)
    mask_error = (~is_empty_code) & (df_final['full_name'].isna())
    df_final.loc[mask_error, 'full_name'] = "⚠️ Lỗi: Mã " + df_final['assigned_to_code'].astype(str)
    df_final.loc[mask_error, 'department'] = "Cần rà soát"
    df_final.loc[mask_error, 'branch'] = "Chưa xác định"

    # 5. TẠO CÁC BẢNG THỐNG KÊ
    df_final['risk_level'] = "🟢 Thấp"
    branch_stats = df_final.groupby('branch').size().reset_index(name='asset_count')
    dept_stats = df_final.groupby('department').size().reset_index(name='asset_count')
    user_stats = df_final.groupby('full_name').size().reset_index(name='assets').sort_values('assets', ascending=False)

    return ai_metrics, df_final, pd.DataFrame(), branch_stats, dept_stats, user_stats
