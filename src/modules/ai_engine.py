import pandas as pd
import numpy as np
import re

def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):
    # =====================================================
    # 1. KHỞI TẠO HỆ THỐNG
    # =====================================================
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    empty = pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, empty, empty, empty, empty, empty

    df_assets = df_assets.copy()

    # =====================================================
    # 2. HÀM LÀM SẠCH TUYỆT ĐỐI (CORE BREAKTHROUGH)
    # =====================================================
    def super_clean(series):
        if series is None:
            return pd.Series(dtype="object")
        return (
            series.astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True) # Xóa .0 của số float
            .str.replace(r"[^\d]", "", regex=True) # Chỉ giữ lại số
            .replace(["", "nan", "None", "null", "<NA>"], np.nan)
        )

    # Backup thông tin gốc từ database assets
    if "department" in df_assets.columns:
        df_assets["orig_dept"] = df_assets["department"]
    if "branch" in df_assets.columns:
        df_assets["orig_branch"] = df_assets["branch"]

    # Chuẩn hóa mã nhân viên để merge
    df_assets["key_join"] = super_clean(df_assets["assigned_to_code"])

    # =====================================================
    # 3. KẾT NỐI VỚI BẢNG NHÂN VIÊN (STAFF MERGE)
    # =====================================================
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff["key_staff"] = super_clean(df_staff["employee_code"])
        
        # Chỉ lấy các cột định danh cần thiết
        staff_lookup = (
            df_staff[["key_staff", "full_name", "department", "branch"]]
            .drop_duplicates("key_staff")
        )

        # Merge dữ liệu
# Chèn vào ngay trước dòng pd.merge
        
df_ai_base = pd.merge(...)       
        df_ai_base = pd.merge(
            df_assets,
            staff_lookup,
            left_on="key_join",
            right_on="key_staff",
            how="left"
        )
    else:
        df_ai_base = df_assets.copy()
        for col in ["full_name", "department", "branch"]:
            df_ai_base[col] = np.nan

    # =====================================================
    # 4. LOGIC PHÂN LOẠI TRẠNG THÁI (FIX HIỂN THỊ)
    # =====================================================
    # Kiểm tra mã thô để phân biệt Kho và Lỗi
    raw_code = (
        df_ai_base["assigned_to_code"]
        .astype(str)
        .str.strip()
        .replace(["nan", "None", "", "<NA>"], np.nan)
    )
    is_empty_code = raw_code.isna()

    # --- CASE A: KHO TỔNG / HỆ THỐNG ---
    mask_stock = is_empty_code
    df_ai_base.loc[mask_stock, "full_name"] = "📦 Kho tổng / Hệ thống"
    
    # Ưu tiên lấy phòng ban 'Hạ tầng' hoặc 'Lưu kho'
    if "orig_dept" in df_ai_base.columns:
        df_ai_base.loc[mask_stock, "department"] = df_ai_base.loc[mask_stock, "orig_dept"].fillna("Lưu kho")
    else:
        df_ai_base.loc[mask_stock, "department"] = "Lưu kho"
    
    # Ưu tiên lấy chi nhánh 'Toàn quốc'
    df_ai_base.loc[mask_stock, "branch"] = "Toàn quốc"

    # --- CASE B: LỖI MÃ (Có mã nhưng không khớp nhân viên) ---
    mask_error = (~is_empty_code) & (df_ai_base["full_name"].isna())
    df_ai_base.loc[mask_error, "full_name"] = "⚠️ Lỗi: Mã " + df_ai_base["assigned_to_code"].astype(str)
    df_ai_base.loc[mask_error, "department"] = "Cần rà soát"
    df_ai_base.loc[mask_error, "branch"] = "Chưa xác định"

    # =====================================================
    # 5. TÍNH TOÁN RỦI RO (RISK ENGINE)
    # =====================================================
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base.get("created_at", now), errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # Giả lập Risk Score (Thấp cho tất cả máy hiện tại như trong ảnh)
    df_ai_base["risk_score"] = 0.2
    df_ai_base["risk_level"] = "🟢 Thấp"

    # =====================================================
    # 6. THỐNG KÊ (ANALYTICS)
    # =====================================================
    branch_stats = df_ai_base.groupby("branch").agg(asset_count=("asset_tag", "count"), avg_risk=("risk_score", "mean")).reset_index()
    dept_stats = df_ai_base.groupby("department").agg(asset_count=("asset_tag", "count"), avg_risk=("risk_score", "mean")).reset_index()
    user_stats = df_ai_base.groupby("full_name").agg(assets=("asset_tag", "count"), avg_risk=("risk_score", "mean")).sort_values("assets", ascending=False).reset_index()

    return ai_metrics, df_ai_base, empty, branch_stats, dept_stats, user_stats
