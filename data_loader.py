import streamlit as st
import pandas as pd

@st.cache_data
def get_cleaned_data(start_date, end_date):
    user = "show0621" 
    repo = "option"
    base_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/"
    
    try:
        # 讀取檔案
        df_fut = pd.read_parquet(base_url + "tx_1h_cache.parquet")
        df_opt = pd.read_parquet(base_url + "txo_full_cache.parquet")
        
        # 轉換為 Datetime 格式
        df_fut['date'] = pd.to_datetime(df_fut['date'])
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        
        # --- 核心修正：統一移除時區資訊 ---
        if df_fut['date'].dt.tz is not None:
            df_fut['date'] = df_fut['date'].dt.tz_localize(None)
        if df_opt['date'].dt.tz is not None:
            df_opt['date'] = df_opt['date'].dt.tz_localize(None)
        
        # 轉換 UI 傳入的日期
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        
        # 進行比較與過濾
        df_fut = df_fut[(df_fut['date'] >= start_ts) & (df_fut['date'] <= end_ts)]
        df_opt = df_opt[(df_opt['date'] >= start_ts) & (df_opt['date'] <= end_ts)]
        
        return df_fut, df_opt
    except Exception as e:
        st.error(f"資料處理失敗: {e}")
        return None, None
