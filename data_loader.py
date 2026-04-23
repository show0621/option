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
        st.error("請檢查 Streamlit Secrets 中的 FINMIND_TOKEN 是否正確。")
        return None, None

    # 1. 抓取期貨資料 (量較小，通常沒問題)
    try:
        df_fut = api.taiwan_futures_daily(
            futures_id='TX', 
            start_date=start_date, 
            end_date=end_date
        )
        if not df_fut.empty:
            df_fut['date'] = pd.to_datetime(df_fut['date'])
            df_fut.set_index('date', inplace=True)
    except Exception as e:
        st.error(f"期貨資料抓取失敗: {e}")
        return None, None

    # 2. 抓取選擇權資料 (改為分年度抓取，避免 JSONDecodeError)
    all_opt = []
    years = pd.date_range(start=start_date, end=end_date, freq='YE').year.tolist()
    if not years or pd.to_datetime(end_date).year not in years:
        years.append(pd.to_datetime(end_date).year)
    
    years = sorted(list(set(years)))

    progress_text = st.empty()
    for year in years:
        progress_text.text(f"正在下載 {year} 年選擇權資料...")
        y_start = f"{year}-01-01" if year > pd.to_datetime(start_date).year else start_date
        y_end = f"{year}-12-31" if year < pd.to_datetime(end_date).year else end_date
        
        try:
            # 增加 retry 機制
            for _ in range(3):
                temp_opt = api.taiwan_option_daily(
                    option_id='TXO', 
                    start_date=y_start, 
                    end_date=y_end
                )
                if not temp_opt.empty:
                    # 篩選必要欄位減少記憶體負擔
                    temp_opt = temp_opt[['date', 'strike_price', 'type', 'settlement_price', 'contract_date']]
                    all_opt.append(temp_opt)
                    break
                time.sleep(1) # 避免過快請求
        except Exception as e:
            st.warning(f"{year} 年資料下載中斷，嘗試跳過...")
            continue

    progress_text.empty()
    
    if not all_opt:
        return df_fut, pd.DataFrame()
        
    df_opt = pd.concat(all_opt).drop_duplicates()
    return df_fut, df_opt
