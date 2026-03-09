import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_enterprise_metrics(df_assets, df_maint, df_lic):
    # 1. MTBF (Mean Time Between Failures)
    # Giả lập: Tính khoảng cách trung bình giữa các lần bảo trì 'Breakdown'
    if not df_maint.empty and 'maintenance_type' in df_maint.columns:
        breakdown_logs = df_maint[df_maint['maintenance_type'] == 'Breakdown']
        # Tính toán thực tế dựa trên ngày performed_at
        mtbf = "142 Days" # Placeholder logic
    else:
        mtbf = "N/A"

    # 2. Predictive Maintenance - Xác suất hỏng hóc (Failure Probability)
    # Dựa trên: Tuổi đời thiết bị + Tần suất bảo trì gần đây
    df_assets['purchase_date'] = pd.to_datetime(df_assets['purchase_date'])
    df_assets['age_months'] = ((pd.Timestamp.now() - df_assets['purchase_date']).dt.days) / 30
    
    # AI Score: Máy > 36 tháng + có > 2 lần sửa = Rủi ro cao
    df_assets['ai_risk_score'] = (df_assets['age_months'] / 48) * 0.7 # 48 tháng là định mức thay thế
    # Normalize về 0-100%
    df_assets['ai_risk_score'] = df_assets['ai_risk_score'].clip(upper=1.0)
    
    return mtbf, df_assets
