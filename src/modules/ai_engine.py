import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    # Khởi tạo các giá trị mặc định
    ai_metrics = {'mtbf': 'N/A', 'mttr': 'N/A'}
    df_ai = pd.DataFrame()

    if df_assets.empty:
        return ai_metrics, df_ai

    # --- 1. CHUẨN HÓA DỮ LIỆU ---
    # Ép kiểu dữ liệu thời gian
    df_assets['created_at'] = pd.to_datetime(df_assets['created_at'])
    now = pd.to_datetime("now", utc=True)

    # Tính tuổi thọ thiết bị (age_days)
    df_assets['age_days'] = (now - df_assets['created_at']).dt.days

    # --- 2. XỬ LÝ LỊCH SỬ BẢO TRÌ ---
    if not df_maint.empty:
        # FIX TẠI ĐÂY: Sử dụng asset_tag thay vì asset_id
        # Đếm số lần sửa chữa cho mỗi asset_tag
        maint_counts = df_maint.groupby('asset_tag').size().reset_index(name='m_count')
        
        # Tính MTTR (Thời gian sửa chữa trung bình) nếu có cột duration
        if 'duration' in df_maint.columns:
            avg_mttr = df_maint['duration'].mean()
            ai_metrics['mttr'] = f"{avg_mttr:.1f} hrs"
    else:
        maint_counts = pd.DataFrame(columns=['asset_tag', 'm_count'])

    # --- 3. TÍNH TOÁN RISK SCORE (AI PREDICTION) ---
    # Gộp dữ liệu bảo trì vào bảng assets
    df_ai = pd.merge(df_assets, maint_counts, on='asset_tag', how='left').fillna({'m_count': 0})

    # Thuật toán tính rủi ro đơn giản:
    # Risk = (Số lần sửa * 0.4) + (Tuổi thọ > 1000 ngày * 0.3) + (Status là 'Active' * 0.1)
    def predict_risk(row):
        score = (row['m_count'] * 0.2) + (min(row['age_days'] / 1095, 1) * 0.5)
        return min(score, 1.0) # Không vượt quá 100%

    df_ai['risk_score'] = df_ai.apply(predict_risk, axis=1)

    # Tính MTBF (Thời gian giữa các lần hỏng) - Giả lập
    if not df_maint.empty:
        total_days = df_assets['age_days'].sum()
        total_failures = df_maint.shape[0]
        if total_failures > 0:
            mtbf = total_days / total_failures
            ai_metrics['mtbf'] = f"{int(mtbf)} days"

    return ai_metrics, df_ai
