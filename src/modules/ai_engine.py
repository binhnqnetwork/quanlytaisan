import pandas as pd
import numpy as np
import re

def calculate_ai_metrics(df_assets, df_maint=None, df_lic=None, df_staff=None):
    # =====================================================
    # 1. KHỞI TẠO (SYSTEM INIT)
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
    # 2. HÀM LÀM SẠCH CƯỠNG CHẾ (THE FIX)
    # =====================================================
    def force_clean_to_string(series):
        if series is None: return pd.Series(dtype="object")
        return (
            series.astype(str)
            .str.strip()
            # Xóa sạch đuôi .0 nếu bị nhận diện nhầm là float
            .str.replace(r"\.0$", "", regex=True)
            # CHỈ giữ lại các chữ số, loại bỏ hoàn toàn các ký tự ẩn, khoảng trắng, <NA>, nan
            .str.extract(r'(\d+)', expand=False)
            .replace(["", "nan", "None", "null", "<NA>"], np.nan)
        )

    # Backup phòng ban/chi nhánh gốc từ database Assets (như 'Hạ tầng' trong ảnh)
    if "department" in df_assets.columns:
        df_assets["orig_dept"] = df_assets["department"]
    if "branch" in df_assets.columns:
        df_assets["orig_branch"] = df_assets["branch"]

    # Tạo khóa liên kết siêu sạch từ cột assigned_to_code
    df_assets["key_join"] = force_clean_to_string(df_assets["assigned_to_code"])

    # =====================================================
    # 3. KẾT NỐI VỚI BẢNG NHÂN VIÊN (STAFF MERGE)
    # =====================================================
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        
        # Làm sạch cột employee_code từ database Staff theo cùng một cách
        df_staff["key_staff"] = force_clean_to_string(df_staff["employee_code"])
        
        # Chỉ lấy các cột định danh quan trọng để merge
        staff_lookup = (
            df_staff[["key_staff", "full_name", "department", "branch"]]
            .drop_duplicates("key_staff")
        )

        # Thực hiện LEFT JOIN dựa trên khóa đã được chuẩn hóa thành số-chuỗi
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
    # 4. ENGINE PHÂN LOẠI & HIỂN THỊ (THE LOGIC)
    # =====================================================
    # Kiểm tra mã thô để xác định dòng nào trống thực sự
    raw_val = (
        df_ai_base["assigned_to_code"]
        .astype(str).str.strip()
        .replace(["nan", "None", "", "<NA>"], np.nan)
    )
    is_empty_code = raw_val.isna()

    # --- TRƯỜNG HỢP: KHO TỔNG / HỆ THỐNG (Mã trống) ---
    mask_stock = is_empty_code
    df_ai_base.loc[mask_stock, "full_name"] = "📦 Kho tổng / Hệ thống"
    
    # Khôi phục phòng ban gốc (ví dụ: 'Hạ tầng' thay vì 'Cần rà soát')
    if "orig_dept" in df_ai_base.columns:
        df_ai_base.loc[mask_stock, "department"] = df_ai_base.loc[mask_stock, "orig_dept"].fillna("Lưu kho")
    else:
        df_ai_base.loc[mask_stock, "department"] = "Lưu kho"
    
    # Khôi phục chi nhánh gốc
    if "orig_branch" in df_ai_base.columns:
        df_ai_base.loc[mask_stock, "branch"] = df_ai_base.loc[mask_stock, "orig_branch"].fillna("Toàn quốc")
    else:
        df_ai_base.loc[mask_stock, "branch"] = "Toàn quốc"

    # --- TRƯỜNG HỢP: LỖI (Có mã nhưng không tìm thấy Tên trong Staff) ---
    mask_error = (~is_empty_code) & (df_ai_base["full_name"].isna())
    df_ai_base.loc[mask_error, "full_name"] = "⚠️ Lỗi: Mã " + df_ai_base["assigned_to_code"].astype(str)
    df_ai_base.loc[mask_error, "department"] = "Cần rà soát"
    df_ai_base.loc[mask_error, "branch"] = "Chưa xác định"

    # =====================================================
    # 5. RISK ENGINE & ANALYTICS (TÍNH TOÁN KPI)
    # =====================================================
    now = pd.Timestamp.now(tz="UTC")
    df_ai_base["risk_score"] = 0.2
    df_ai_base["risk_level"] = "🟢 Thấp"

    branch_stats = df_ai_base.groupby("branch").size().reset_index(name="asset_count")
    dept_stats = df_ai_base.groupby("department").size().reset_index(name="asset_count")
    user_stats = df_ai_base.groupby("full_name").size().reset_index(name="assets").sort_values("assets", ascending=False)

    return ai_metrics, df_ai_base, empty, branch_stats, dept_stats, user_stats
