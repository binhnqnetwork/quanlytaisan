import pandas as pd
import numpy as np
import json

def calculate_ai_metrics(df_assets, df_maint, df_lic, df_staff=None):
    """
    Hệ thống phân tích tài sản thông minh - Tối ưu cho dữ liệu thực tế Supabase.
    Bổ sung df_staff để mapping Tên nhân viên và Chi nhánh chính xác.
    """
    # 1. KHỞI TẠO MẶC ĐỊNH
    ai_metrics = {
        "mtbf": "N/A", "mttr": "N/A",
        "critical_assets": 0, "high_risk_assets": 0, "license_alerts": 0
    }
    df_ai, license_ai = pd.DataFrame(), pd.DataFrame()
    branch_stats, dept_stats, user_stats = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    if df_assets is None or df_assets.empty:
        return ai_metrics, df_ai, license_ai, branch_stats, dept_stats, user_stats

    # -------------------------------------------------
    # 2. CHUẨN HÓA DỮ LIỆU & AI MAPPING (STAFF & ASSETS)
    # -------------------------------------------------
    now = pd.Timestamp.utcnow()
    df_assets = df_assets.copy()

    # Nối với bảng Staff để lấy Full Name, Department và Branch thực tế
    if df_staff is not None and not df_staff.empty:
        df_ai_base = pd.merge(
            df_assets, 
            df_staff[['employee_code', 'full_name', 'department', 'branch']], 
            left_on='assigned_to_code', 
            right_on='employee_code', 
            how='left'
        )
        # Xử lý trường hợp máy trong kho (không có nhân viên)
        df_ai_base['full_name'] = df_ai_base['full_name'].fillna("Kho tổng / Hệ thống")
        df_ai_base['department'] = df_ai_base['department'].fillna("Hạ tầng")
        df_ai_base['branch'] = df_ai_base['branch'].fillna(df_ai_base['asset_tag'].str.split('-').str[-1])
    else:
        # Fallback nếu không có bảng staff
        df_ai_base = df_assets.copy()
        df_ai_base['full_name'] = df_ai_base['assigned_to_code'].fillna("Kho tổng")
        df_ai_base['branch'] = df_ai_base['asset_tag'].str.split('-').str[-1]
        if 'department' not in df_ai_base.columns:
            df_ai_base['department'] = "Khối Văn phòng"

    # Xử lý thời gian
    df_ai_base["created_at"] = pd.to_datetime(df_ai_base["created_at"], errors="coerce", utc=True).fillna(now)
    df_ai_base["age_days"] = (now - df_ai_base["created_at"]).dt.days

    # -------------------------------------------------
    # 3. PHÂN TÍCH BẢO TRÌ (MTBF/MTTR) - Đếm từ maintenance_history
    # -------------------------------------------------
    # Thay vì dùng bảng df_maint riêng, ta đếm trực tiếp từ cột maintenance_history (list) của assets
    df_ai_base['m_count'] = df_ai_base['maintenance_history'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    # Tính MTTR giả định nếu có dữ liệu trong m_history (hoặc dùng df_maint nếu có)
    if df_maint is not None and not df_maint.empty:
        df_maint["performed_at"] = pd.to_datetime(df_maint["performed_at"], errors="coerce", utc=True)
        if "duration" in df_maint.columns:
            ai_metrics["mttr"] = f"{df_maint['duration'].median():.1f} giờ"

    # -------------------------------------------------
    # 4. MÔ HÌNH RỦI RO CHUYÊN SÂU (ADVANCED RISK MODEL)
    # -------------------------------------------------
    def get_spec_risk(spec_str):
        try:
            if not spec_str: return 0.5
            s = str(spec_str).lower()
            if 'i3' in s or '4gb' in s: return 0.9  # Rủi ro rất cao vì dễ treo máy
            if 'i7' in s or '16gb' in s or '32gb' in s: return 0.2
            return 0.5
        except: return 0.5

    df_ai_base['spec_score'] = df_ai_base['specs'].apply(get_spec_risk)

    # Trọng số rủi ro: 40% Lịch sử hỏng - 30% Tuổi thọ - 30% Cấu hình
    fail_f = np.minimum(df_ai_base["m_count"] / 3, 1) # 3 lần hỏng là max risk
    age_f = np.minimum(df_ai_base["age_days"] / (365 * 3), 1) # 3 năm là máy cũ
    
    df_ai_base["risk_score"] = (0.4 * fail_f + 0.3 * age_f + 0.3 * df_ai_base['spec_score'])
    
    df_ai_base["risk_level"] = np.select(
        [df_ai_base["risk_score"] >= 0.7, df_ai_base["risk_score"] >= 0.4],
        ["🔴 Nguy cấp", "🟠 Cao"], default="🟢 Thấp"
    )

    # -------------------------------------------------
    # 5. THỐNG KÊ CHI TIẾT (BRANCH / USER)
    # -------------------------------------------------
    # Thống kê chi nhánh
    branch_stats = df_ai_base.groupby('branch').agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'mean'
    }).rename(columns={'asset_tag': 'Số máy', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro TB'}).reset_index()

    # Thống kê người dùng (Top 10 rủi ro)
    user_stats = df_ai_base.groupby(['assigned_to_code', 'full_name', 'department', 'branch']).agg({
        'asset_tag': 'count', 
        'm_count': 'sum', 
        'risk_score': 'max'
    }).rename(columns={'asset_tag': 'Máy giữ', 'm_count': 'Tổng lượt hỏng', 'risk_score': 'Rủi ro Max'}).reset_index()
    
    user_stats = user_stats.sort_values('Tổng lượt hỏng', ascending=False).head(10)

    # -------------------------------------------------
    # 6. LICENSE ANALYTICS
    # -------------------------------------------------
    if df_lic is not None and not df_lic.empty:
        license_ai = df_lic.copy()
        
        # Đồng bộ tên cột theo bảng thực tế của bạn
        # Cột 'name' trong DB -> đổi thành 'software_name' để hiển thị
        license_ai = license_ai.rename(columns={'name': 'software_name'})
        
        # Tính toán dựa trên số lượng thực tế
        license_ai["remaining"] = license_ai["total_quantity"] - license_ai["used_quantity"]
        
        # Tránh lỗi chia cho 0 nếu total_quantity = 0
        license_ai["usage_ratio"] = (license_ai["used_quantity"] / license_ai["total_quantity"]).replace([np.inf, -np.inf], 0).fillna(0)
        
        # AI Logic: Cảnh báo dựa trên alert_threshold từ Database của bạn
        # Nếu số lượng còn lại <= ngưỡng thiết lập, đánh dấu Nguy cấp
        license_ai["license_risk"] = np.select(
            [
                license_ai["remaining"] <= license_ai["alert_threshold"],
                license_ai["usage_ratio"] >= 0.9
            ],
            ["🚨 Sắp hết hạn mức", "⚠️ Sử dụng cao"], 
            default="✅ Ổn định"
        )
        
        # Đếm số lượng license cần chú ý cho KPI Card
        ai_metrics["license_alerts"] = int((license_ai["remaining"] <= license_ai["alert_threshold"]).sum())

    # ... (trả về các giá trị) ...
    return ai_metrics, df_ai_base, license_ai, branch_stats, dept_stats, user_stats
2. Cập nhật src/modules/dashboard.py
Phần này đã được tối ưu để hiển thị bảng Truy xuất Chi tiết theo đúng ảnh mẫu bạn gửi: Bỏ "Cấu hình", thêm "Nhân viên" và "Phòng ban".

Python
def render_dashboard(supabase):
    # ... (Phần KPI Cards và Biểu đồ giữ nguyên như bản trước) ...

    # 5. HIỂN THỊ BẢNG LICENSE (Sau khi đã sửa tên cột ở Engine)
    if not lic_ai.empty:
        st.markdown("---")
        st.subheader("🌐 Tình trạng Bản quyền & Phần mềm")
        
        # Lọc ra các license có vấn đề hoặc sắp hết
        risk_licenses = lic_ai[lic_ai['license_risk'] != "✅ Ổn định"]
        
        if not risk_licenses.empty:
            st.warning(f"Phát hiện {len(risk_licenses)} phần mềm cần lưu ý.")
            st.dataframe(
                risk_licenses[['software_name', 'expiry_date', 'used_quantity', 'total_quantity', 'remaining', 'license_risk']]
                .rename(columns={
                    'software_name': 'Tên Phần mềm',
                    'expiry_date': 'Ngày hết hạn',
                    'used_quantity': 'Đã dùng',
                    'total_quantity': 'Tổng cấp',
                    'remaining': 'Còn lại',
                    'license_risk': 'Trạng thái'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.success("Tất cả bản quyền đang ở trạng thái an toàn.")

def render_usage_details(supabase):
    st.header("👥 Truy xuất Chi tiết Cấp phát License & Nhân sự")
    
    try:
        # Tải dữ liệu
        df_assets = pd.DataFrame(supabase.table("assets").select("*").execute().data)
        df_staff = pd.DataFrame(supabase.table("staff").select("employee_code, full_name, department, branch").execute().data)

        if not df_assets.empty and not df_staff.empty:
            # Join dữ liệu Assets và Staff
            df_final = pd.merge(df_assets, df_staff, left_on='assigned_to_code', right_on='employee_code', how='left')

            # Xử lý chuỗi phần mềm
            df_final['software_display'] = df_final['software_list'].apply(lambda x: ", ".join(x) if isinstance(x, list) else "Trống")

            # Giao diện lọc
            search_col, branch_col = st.columns([2, 1])
            with search_col:
                search = st.text_input("🔍 Tìm theo Mã NV, Phần mềm (Photoshop, Office...)", placeholder="Nhập từ khóa...")
            with branch_col:
                branches = [b for b in df_final['branch'].unique() if b]
                branch_sel = st.multiselect("Lọc theo Vùng miền", options=branches, default=branches)

            # Logic lọc
            mask = df_final['branch'].isin(branch_sel)
            if search:
                mask = mask & (
                    df_final['full_name'].str.contains(search, case=False, na=False) |
                    df_final['software_display'].str.contains(search, case=False) |
                    df_final['assigned_to_code'].astype(str).str.contains(search)
                )

            # Hiển thị bảng đúng như format yêu cầu (Bỏ Cấu hình)
            st.dataframe(
                df_final[mask][[
                    'asset_tag', 'assigned_to_code', 'full_name', 'department', 'branch', 'software_display', 'status'
                ]].rename(columns={
                    'asset_tag': 'Mã Máy',
                    'assigned_to_code': 'Mã NV',
                    'full_name': 'Tên Nhân Viên',
                    'department': 'Phòng Ban',
                    'branch': 'Vùng miền',
                    'software_display': 'Bản quyền đang dùng',
                    'status': 'Trạng thái'
                }),
                use_container_width=True, hide_index=True
            )
    except Exception as e:
        st.error(f"Lỗi: {e}")
