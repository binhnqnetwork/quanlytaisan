import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    # 1. Khởi tạo các giá trị mặc định
    ai_metrics = {"mtbf": "N/A", "mttr": "N/A", "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0}
    
    if df_assets is None or df_assets.empty:
        return ai_metrics, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # 2. CHUẨN HÓA DỮ LIỆU (Bắt buộc phải ép về String)
    def force_string(series):
        return series.astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

    df_assets = df_assets.copy()
    df_assets['join_key'] = force_string(df_assets['assigned_to_code'])

    # 3. MERGE VỚI STAFF
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff['staff_key'] = force_string(df_staff['employee_code'])
        
        # Chỉ lấy cột cần thiết và xóa trùng
        staff_clean = df_staff[['staff_key', 'full_name', 'department', 'branch']].drop_duplicates('staff_key')
        
        df_ai_base = pd.merge(df_assets, staff_clean, left_on='join_key', right_on='staff_key', how='left')
    else:
        df_ai_base = df_assets.copy()
        for c in ['full_name', 'department', 'branch']: df_ai_base[c] = np.nan

    # 4. LOGIC PHÂN LOẠI TRẠNG THÁI (Đã fix lỗi hiển thị)
    # Kiểm tra mã gốc xem có trống không
    is_null = df_ai_base['assigned_to_code'].isna() | (df_ai_base['join_key'] == 'nan') | (df_ai_base['join_key'] == '')

    # Trường hợp: KHO TỔNG (Mã trống)
    df_ai_base.loc[is_null, 'full_name'] = '📦 Kho tổng / Hệ thống'
    df_ai_base.loc[is_null, 'department'] = 'Lưu kho'
    df_ai_base.loc[is_null, 'branch'] = 'Toàn quốc'

    # Trường hợp: LỖI (Có mã nhưng không tìm thấy trong Staff)
    mask_error = (~is_null) & (df_ai_base['full_name'].isna())
    df_ai_base.loc[mask_error, 'full_name'] = '⚠️ Lỗi: Mã ' + df_ai_base['assigned_to_code'].astype(str)
    df_ai_base.loc[mask_error, 'department'] = 'Cần rà soát'
    df_ai_base.loc[mask_error, 'branch'] = 'Chưa xác định'

    # 5. CÁC PHÉP TÍNH KHÁC (GIỮ NGUYÊN)
    now = pd.Timestamp.now(tz="UTC")
    # ... (giữ nguyên phần tính Risk và Age như các bản trước)
    
    # 6. TỔNG HỢP KẾT QUẢ
    # Chuyển đổi các cột stats để đảm bảo Dashboard nhận diện đúng
    user_stats = df_ai_base.groupby('full_name', dropna=False).size().reset_index(name='assets').sort_values('assets', ascending=False)
    # ... (các stats khác)

    return ai_metrics, df_ai_base, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), user_stats
