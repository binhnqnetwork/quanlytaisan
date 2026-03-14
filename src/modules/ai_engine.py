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
    # 2. HÀM CHUẨN HÓA TRIỆT ĐỂ (THE FINAL FIX)
    # =====================================================
    def ultra_normalize(series):
        if series is None: return pd.Series(dtype="object")
        return (
            series.astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True) # Xử lý số float bị biến thành chuỗi
            .str.extract(r'(\d+)', expand=False)  # CHỈ trích xuất số, bỏ qua mọi ký tự lạ ẩn
            .replace(["nan", "None", "", "<NA>"], np.nan)
        )

    # Sao lưu thông tin phòng ban/chi nhánh gốc từ database Assets
    if "department" in df_assets.columns:
        df_assets["orig_dept"] = df_assets["department"]
    if "branch" in df_assets.columns:
        df_assets["orig_branch"] = df_assets["branch"]

    # Tạo khóa liên kết sạch
    df_assets["key_join"] = ultra_normalize(df_assets["assigned_to_code"])

    # =====================================================
    # 3. KẾT NỐI VỚI BẢNG NHÂN VIÊN (STAFF MERGE)
    # =====================================================
    if df_staff is not None and not df_staff.empty:
        df_staff = df_staff.copy()
        df_staff["key_staff"] = ultra_normalize(df_staff["employee_code"])
        
        # Chỉ lấy các cột định danh quan trọng để tránh trùng lặp máy
        staff_lookup = (
            df_staff[["key_staff", "full_name", "department", "branch"]]
            .drop_duplicates("key_staff")
        )

        # Thực hiện Left Join
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
    # 4. ENGINE PHÂN LOẠI HIỂN THỊ
    # =====================================================
    # Kiểm tra mã thô để phân biệt máy rỗng (Kho) và máy gán lỗi
    raw_val = (
        df_ai_base["assigned_to_code"]
        .astype(str).str.strip()
        .replace(["nan", "None", "", "<NA>"], np.nan)
    )
    is_empty_code = raw_val.isna()

    # --- CASE A: KHO TỔNG / HỆ THỐNG (PC0001-HCM rơi vào đây) ---
    mask_stock = is_empty_code
    df_ai_base.loc[mask_stock, "full_name"] = "📦 Kho tổng / Hệ thống"
    
    # Khôi phục dữ liệu gốc từ Assets cho máy kho
    if "orig_dept" in df_ai_base.columns:
        df_ai_base.loc[mask_stock, "department"] = df_ai_base.loc[mask_stock, "orig_dept"].fillna("Lưu kho")
    else:
        df_ai_base.loc[mask_stock, "department"] = "Lưu kho"
    
    df_ai_base.loc[mask_stock, "branch"] = "Toàn quốc"

    # --- CASE B: LỖI MÃ (Mã có tồn tại nhưng Merge thất bại) ---
    mask_error = (~is_empty_code) & (df_ai_base["full_name"].isna())
    df_ai_base.loc[mask_error, "full_name"] = "⚠️ Lỗi: Mã " + df_ai_base["assigned_to_code"].astype(str)
    df_ai_base.loc[mask_error, "department"] = "Cần rà soát"
    df_ai_base.loc[mask_error, "branch"] = "Chưa xác định"

    # =====================================================
    # 5. TÍNH TOÁN RỦI RO & THỐNG KÊ (KPI)
    # =====================================================
    df_ai_base["risk_score"] = 0.2
    df_ai_base["risk_level"] = "🟢 Thấp"

    branch_stats = df_ai_base.groupby("branch").size().reset_index(name="asset_count")
    dept_stats = df_ai_base.groupby("department").size().reset_index(name="asset_count")
    user_stats = df_ai_base.groupby("full_name").size().reset_index(name="assets").sort_values("assets", ascending=False)

    return ai_metrics, df_ai_base, empty, branch_stats, dept_stats, user_stats
