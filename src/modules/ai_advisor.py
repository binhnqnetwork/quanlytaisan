import streamlit as st
import pandas as pd
from datetime import datetime, date

def render_ai_advisor(supabase):
    st.markdown('<h1 style="font-weight: 700;">🤖 AI Predictive Maintenance</h1>', unsafe_allow_html=True)
    st.info("Hệ thống AI đang phân tích dữ liệu thực tế để đưa ra dự báo vận hành.")

    # 1. LẤY DỮ LIỆU TỔNG HỢP
    res_assets = supabase.table("assets").select("*, maintenance_log(*)").execute()
    
    if not res_assets.data:
        st.warning("Cần thêm dữ liệu bảo trì để AI có thể phân tích.")
        return

    df = pd.DataFrame(res_assets.data)
    today = date.today()

    # 2. XỬ LÝ LOGIC DỰ BÁO (AI ENGINE)
    predictions = []
    
    for _, row in df.iterrows():
        logs = row.get('maintenance_log', [])
        score = 0
        reasons = []
        action = "✅ Bình thường"
        
        # Kiểm tra tuổi thọ máy (Giả định dựa trên asset_tag hoặc ngày tạo)
        # Ở đây ta check số lần sửa chữa
        repair_count = len([l for l in logs if l['action_type'] in ['Sửa chữa', 'Thay thế']])
        
        # Quy tắc 1: Tần suất sửa chữa quá cao
        if repair_count >= 3:
            score += 40
            reasons.append("Tần suất hỏng hóc cao (>3 lần/năm)")
            
        # Quy tắc 2: Cấu hình yếu (Phân tích text trong specs)
        specs_str = str(row.get('specs', '')).lower()
        if '4gb' in specs_str or 'hdd' in specs_str:
            score += 30
            reasons.append("Cấu hình lạc hậu (RAM thấp hoặc dùng ổ HDD)")
            
        # Quy tắc 3: Quá hạn bảo trì định kỳ
        last_maint = None
        if logs:
            last_maint = max([datetime.strptime(l['performed_at'], '%Y-%m-%d').date() for l in logs])
            days_since = (today - last_maint).days
            if days_since > 180:
                score += 20
                reasons.append(f"Đã quá hạn bảo trì định kỳ ({days_since} ngày)")

        # Phân loại hành động
        if score >= 60: action = "🚨 ĐỀ XUẤT THAY MỚI"
        elif score >= 30: action = "⚠️ CẦN NÂNG CẤP/KIỂM TRA"
        
        if score > 0:
            predictions.append({
                "Mã máy": row['asset_tag'],
                "Trạng thái hiện tại": row['status'],
                "Đánh giá rủi ro": f"{score}%",
                "Phân tích từ AI": " | ".join(reasons),
                "Hành động khuyến nghị": action
            })

    # 3. HIỂN THỊ GIAO DIỆN AI
    df_predict = pd.DataFrame(predictions)
    
    if not df_predict.empty:
        # Dashboard tóm tắt
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Máy cần thay thế ngay", len(df_predict[df_predict['Hành động khuyến nghị'] == "🚨 ĐỀ XUẤT THAY MỚI"]))
        with c2:
            st.metric("Máy cần nâng cấp", len(df_predict[df_predict['Hành động khuyến nghị'] == "⚠️ CẦN NÂNG CẤP/KIỂM TRA"]))

        st.markdown("---")
        st.subheader("📋 Danh sách dự báo chi tiết")
        
        # Hiển thị bảng dự báo với màu sắc
        def color_action(val):
            color = 'red' if 'THAY MỚI' in val else ('orange' if 'NÂNG CẤP' in val else 'black')
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            df_predict.style.applymap(color_action, subset=['Hành động khuyến nghị']),
            use_container_width=True,
            hide_index=True
        )
        
        # Nút xuất báo cáo AI
        st.download_button(
            "📥 Xuất báo cáo dự báo (Excel)",
            df_predict.to_csv(index=False).encode('utf-8-sig'),
            "AI_Forecast_Report.csv",
            "text/csv"
        )
    else:
        st.success("🌟 AI phân tích: Hệ thống thiết bị của bạn hiện tại đang vận hành rất tốt!")
