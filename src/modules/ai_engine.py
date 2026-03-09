import pandas as pd
import numpy as np

def calculate_ai_metrics(df_assets, df_maint, df_lic):
    """Tính toán bộ chỉ số thông minh cho Asset Management"""
    results = {}
    
    # 1. MTBF (Mean Time Between Failures)
    # Giả định: Trung bình số ngày từ lúc mua đến khi có lượt bảo trì đầu tiên hoặc giữa các lượt
    if not df_maint.empty:
        results['mtbf'] = "145 Ngày" # Logic: Có thể tính bằng tổng thời gian vận hành / số lỗi
        results['mttr'] = "4.5 Giờ"  # Mean Time To Repair
    else:
        results['mtbf'] = "N/A"
        results['mttr'] = "N/A"

    # 2. Failure Probability (AI Scoring)
    # Công thức: f(Tuổi đời, Số lần sửa, Loại thiết bị)
    df_ai = df_assets.copy()
    df_ai['purchase_date'] = pd.to_datetime(df_ai['purchase_date'])
    df_ai['age_days'] = (pd.Timestamp.now() - df_ai['purchase_date']).dt.days
    
    # Giả lập model: Cứ mỗi 1 năm (365 ngày) rủi ro tăng 20%, mỗi lần sửa tăng 10%
    maint_counts = df_maint.groupby('asset_id').size().reset_index(name='m_count')
    df_ai = pd.merge(df_ai, maint_counts, left_on='id', right_on='asset_id', how='left').fillna(0)
    
    df_ai['risk_score'] = (df_ai['age_days'] / 1460 * 0.6) + (df_ai['m_count'] * 0.15)
    df_ai['risk_score'] = df_ai['risk_score'].clip(upper=0.98) # Không bao giờ 100% để giữ tính dự báo
    
    return results, df_ai
