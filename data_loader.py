import streamlit as st
import pandas as pd

@st.cache_data
def get_cleaned_data(start_date, end_date):
    # 修改為你的 GitHub 原始連結
    # 格式: https://raw.githubusercontent.com/你的名字/倉庫名/main/檔名
    user = "你的GitHub帳號" 
    repo = "option"
    base_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/"
    
    try:
        # 直接讀取備份
        df_fut = pd.read_parquet(base_url + "tx_full_cache.parquet")
        df_opt = pd.read_parquet(base_url + "txo_full_cache.parquet")
        
        # 轉換日期索引以便過濾
        df_fut.index = pd.to_datetime(df_fut.index)
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        
        # 過濾日期
        df_fut = df_fut[(df_fut.index >= start_date) & (df_fut.index <= end_date)]
        df_opt = df_opt[(df_opt['date'] >= start_date) & (df_opt['date'] <= end_date)]
        
        return df_fut, df_opt
    except Exception as e:
        st.error(f"GitHub 資料載入失敗，請確認檔案已上傳: {e}")
        return None, None
