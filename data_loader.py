import streamlit as st
import pandas as pd

@st.cache_data
def get_cleaned_data(start_date, end_date):
    # 請將 show0621 替換為你的 GitHub 帳號
    user = "show0621" 
    repo = "option"
    base_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/"
    
    try:
        # 1. 讀取小時線期貨資料 (1H / 60K)
        df_fut = pd.read_parquet(base_url + "tx_1h_cache.parquet")
        # 2. 讀取選擇權日資料
        df_opt = pd.read_parquet(base_url + "txo_full_cache.parquet")
        
        # 格式轉換
        df_fut['date'] = pd.to_datetime(df_fut['date'])
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        
        # 過濾日期範圍
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        
        df_fut = df_fut[(df_fut['date'] >= start_ts) & (df_fut['date'] <= end_ts)]
        df_opt = df_opt[(df_opt['date'] >= start_ts) & (df_opt['date'] <= end_ts)]
        
        return df_fut, df_opt
    except Exception as e:
        st.error(f"資料載入失敗: {e}")
        return None, None
