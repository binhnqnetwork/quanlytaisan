import streamlit as st
import pandas as pd
from datetime import datetime

def render_licenses(supabase):
    st.header("🌐 Quản lý Bản quyền & License")
    
    # Truy vấn dữ liệu từ bảng licenses
    res = supabase.table("licenses").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu bản quyền.")
