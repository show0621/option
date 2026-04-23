import streamlit as st
from FinMind.data import DataLoader
import pandas as pd
import time

api = DataLoader()

@st.cache_data(ttl=3600)
def get_cleaned_data(start_date, end_date):
    try:
        token = st.secrets["FINMIND_TOKEN"]
        api.login_by_token(api_token=token)
    except:
        st.error("FinMind Token 驗證失敗，請檢查 Secrets。")
        return None, None

    # 1. 抓取期貨資料 (基準)
    try:
        df_fut = api.taiwan_futures_daily(futures_id='TX', start_date=start_date, end_date=end_date)
        if df_fut.empty: return None, None
        df_fut['date'] = pd.to_datetime(df_fut['date'])
        df_fut.set_index('date', inplace=True)
    except:
        return None, None

    # 2. 抓取選擇權 (使用 10 天為單位的極小分段)
    date_chunks = pd.date_range(start=start_date, end=end_date, freq='10D')
    all_opt = []
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, chunk_start in enumerate(date_chunks):
        chunk_end = (chunk_start + pd.Timedelta(days=9)).strftime('%Y-%m-%d')
        s_str = chunk_start.strftime('%Y-%m-%d')
        
        status_text.text(f"📥 正在抓取: {s_str} 至 {chunk_end} ...")
        
        # 增加重試與強制冷卻
        for retry in range(3):
            try:
                time.sleep(0.5) # 強制休息 0.5 秒，保護 API
                temp_opt = api.taiwan_option_daily(
                    option_id='TXO', 
                    start_date=s_str, 
                    end_date=chunk_end
                )
                if not temp_opt.empty:
                    temp_opt = temp_opt[['date', 'strike_price', 'type', 'settlement_price', 'contract_date']]
                    all_opt.append(temp_opt)
                    break
            except:
                time.sleep(2) # 噴錯就休息久一點再試
                continue
        
        progress_bar.progress((i + 1) / len(date_chunks))

    status_text.empty()
    progress_bar.empty()

    if not all_opt:
        return df_fut, pd.DataFrame()
        
    df_opt = pd.concat(all_opt).drop_duplicates()
    return df_fut, df_opt
