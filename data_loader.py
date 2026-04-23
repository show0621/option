import streamlit as st
import pandas as pd

@st.cache_data
def get_cleaned_data(start_date, end_date):
    # 根據你的 GitHub 截圖設定路徑
    user = "show0621" 
    repo = "option"
    # 使用 GitHub Raw 連結來讀取檔案
    base_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/"
    
    try:
        # 1. 讀取期貨備份
        df_fut = pd.read_parquet(base_url + "tx_full_cache.parquet")
        # 2. 讀取選擇權備份
        df_opt = pd.read_parquet(base_url + "txo_full_cache.parquet")
        
        # --- 資料格式處理 ---
        # 確保日期欄位是 datetime 格式
        if 'date' in df_fut.columns:
            df_fut['date'] = pd.to_datetime(df_fut['date'])
            df_fut.set_index('date', inplace=True)
        else:
            df_fut.index = pd.to_datetime(df_fut.index)
            
        df_opt['date'] = pd.to_datetime(df_opt['date'])
        
        # --- 根據介面選擇的日期進行過濾 ---
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        
        df_fut = df_fut[(df_fut.index >= start_ts) & (df_fut.index <= end_ts)]
        df_opt = df_opt[(df_opt['date'] >= start_ts) & (df_opt['date'] <= end_ts)]
        
        if df_fut.empty or df_opt.empty:
            st.warning("所選日期範圍內沒有資料，請調整日期（建議選擇 2024-2025 區間）。")
            
        return df_fut, df_opt

    except Exception as e:
        st.error(f"❌ 從 GitHub 載入資料失敗: {e}")
        st.info("請確認你的 GitHub 倉庫是 Public (公開)，且檔案名稱正確。")
        return None, None
