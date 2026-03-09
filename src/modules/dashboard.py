import streamlit as st
import plotly.express as px
import pandas as pd

def render_dashboard(supabase):
    st.title("📊 Hệ thống Báo cáo Tài sản")
    
    # Lấy dữ liệu assets kết hợp staff
    res = supabase.table("assets").select("*, staff(*)").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        
        # Chỉ số nhanh (KPIs)
        m1, m2, m3 = st.columns(3)
        m1.metric("Tổng thiết bị", len(df))
        m2.metric("Máy chủ (Servers)", len(df[df['type'] == 'Server']))
        m3.metric("Sẵn sàng cấp", len(df[df['status'] == 'Trong kho']))
        
        # Biểu đồ cơ cấu
        fig = px.pie(df, names='type', hole=0.4, title="Tỷ lệ loại tài sản")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu để thống kê.")
