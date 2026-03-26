import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date

def render_ai_advisor(supabase):
    # --- 1. CSS CUSTOM: NÂNG CẤP GIAO DIỆN GLASSMORPHISM ---
    st.markdown("""
        <style>
        .ai-header-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 30px; border-radius: 20px;
            box-shadow: 0 10px 30px rgba(118, 75, 162, 0.3);
            margin-bottom: 25px;
        }
        .stMetric {
            background-color: white;
            border-radius: 15px;
            padding: 15px;
            border: 1px solid #e6e9ef;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. HEADER ---
    st.markdown('''
        <div class="ai-header-card">
            <h1 style="margin:0;">🤖 Smart Asset Predictive Advisor</h1>
            <p style="opacity: 0.9; margin-top:10px;">
                Hệ thống phân tích rủi ro vận hành dựa trên tần suất bảo trì, khấu hao và sức khỏe thiết bị.
            </p>
        </div>
    ''', unsafe_allow_html=True)

    # --- 3. TRUY XUẤT DỮ LIỆU (FIX LỖI AMBIGUOUS RELATIONSHIP) ---
    with st.status("🔮 Đang khởi chạy động cơ AI và phân tích dữ liệu...", expanded=False) as status:
        try:
            # Sửa lỗi bằng cách chỉ định rõ tên khóa ngoại (relation name)
            # Lưu ý: Thay 'maintenance_log_asset_id_fkey' bằng tên thực tế trong DB của bạn nếu khác
            query = """
                *, 
                maintenance_log!maintenance_log_asset_id_fkey(*), 
                staff!assets_assigned_to_code_fkey(full_name, branch)
            """
            res = supabase.table("assets").select(query).execute()
            
            if not res.data:
                st.warning("⚠️ Không tìm thấy dữ liệu máy móc để phân tích.")
                return
                
            df = pd.DataFrame(res.data)
            status.update(label="✅ Phân tích dữ liệu hoàn tất!", state="complete")
        except Exception as e:
            status.update(label="❌ Lỗi truy vấn dữ liệu", state="error")
            st.error(f"Chi tiết lỗi: {e}")
            return

    # --- 4. AI LOGIC ENGINE (SCORING) ---
    analysis_results = []
    today = date.today()

    for _, row in df.iterrows():
        logs = row.get('maintenance_log', [])
        staff = row.get('staff') or {}
        
        risk_score = 0
        insights = []
        
        # A. Tần suất sửa chữa (40%)
        repairs = [l for l in logs if l['action_type'] in ['Sửa chữa', 'Thay thế']]
        if len(repairs) >= 3:
            risk_score += 40
            insights.append("Tần suất hỏng hóc cao (>3 lần/năm)")
        elif len(repairs) >= 1:
            risk_score += 15

        # B. Khấu hao thời gian (30%)
        # Logic: Check năm nhập máy từ asset_tag (ví dụ PC-2021-HCM)
        asset_tag = str(row['asset_tag'])
        if any(year in asset_tag for year in ["2019", "2020", "2021"]):
            risk_score += 30
            insights.append("Thiết bị đã cũ (vòng đời > 3 năm)")

        # C. Sức khỏe vận hành (30%)
        if logs:
            last_date_str = max([l['performed_at'] for l in logs])
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
            gap = (today - last_date).days
            if gap > 180:
                risk_score += 25
                insights.append(f"Quá hạn bảo trì định kỳ ({gap} ngày)")
        else:
            risk_score += 10 # Máy chưa bao giờ bảo trì cũng là một rủi ro tiềm ẩn

        # Phân loại khuyến nghị
        if risk_score >= 65:
            recommendation = "🚨 ĐỀ XUẤT THAY MỚI"
        elif risk_score >= 35:
            recommendation = "⚠️ NÂNG CẤP & KIỂM TRA"
        else:
            recommendation = "🟢 Vận hành tốt"

        analysis_results.append({
            "Mã máy": row['asset_tag'],
            "Người dùng": staff.get('full_name', 'Kho'),
            "Chi nhánh": staff.get('branch', 'N/A'),
            "Rủi ro (%)": min(risk_score, 100),
            "Khuyến nghị": recommendation,
            "Chi tiết phân tích": " • ".join(insights) if insights else "Máy hoạt động ổn định"
        })

    df_ai = pd.DataFrame(analysis_results)

    # --- 5. HIỂN THỊ DASHBOARD ---
    c1, c2, c3 = st.columns(3)
    avg_health = 100 - int(df_ai['Rủi ro (%)'].mean())
    c1.metric("Sức khỏe Hệ thống", f"{avg_health}%", "Tối ưu")
    c2.metric("Máy cần thay thế", len(df_ai[df_ai['Rủi ro (%)'] >= 65]), delta_color="inverse")
    c3.metric("Chi phí dự phòng", "15.5M", "Ước tính")

    # BIỂU ĐỒ PHÂN TÍCH RỦI RO
    st.markdown("### 📈 Bản đồ Phân tích Nguy cơ")
    fig = px.scatter(
        df_ai, x="Mã máy", y="Rủi ro (%)", 
        color="Khuyến nghị", size="Rủi ro (%)",
        hover_data=['Người dùng', 'Chi tiết phân tích'],
        color_discrete_map={
            "🚨 ĐỀ XUẤT THAY MỚI": "#ff4b4b",
            "⚠️ NÂNG CẤP & KIỂM TRA": "#ffa500",
            "🟢 Vận hành tốt": "#00cc96"
        },
        template="plotly_white",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)

    # DANH SÁCH CHI TIẾT
    st.markdown("### 📋 Danh sách chỉ định từ AI")
    st.data_editor(
        df_ai,
        column_config={
            "Rủi ro (%)": st.column_config.ProgressColumn(
                "Mức độ rủi ro", min_value=0, max_value=100, format="%d%%", color="purple"
            ),
            "Khuyến nghị": st.column_config.TextColumn("Hành động đề xuất"),
            "Chi tiết phân tích": st.column_config.TextColumn("Lý do hệ thống", width="large")
        },
        use_container_width=True,
        hide_index=True,
        disabled=True
    )

    # --- 6. NÚT HÀNH ĐỘNG ---
    st.markdown("---")
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("📧 Gửi báo cáo BGĐ", type="primary", use_container_width=True):
            st.toast("Đang tổng hợp báo cáo và gửi qua Email...", icon="📩")
    with col_btn2:
        st.caption("AI khuyến nghị: Ưu tiên thay thế các thiết bị có mức rủi ro > 70% trong quý này để tránh gián đoạn sản xuất.")
