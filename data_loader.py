import streamlit as st
from FinMind.data import DataLoader
import pandas as pd
import datetime

# 初始化 FinMind (建議放在外面)
api = DataLoader()

@st.cache_data(ttl=3600) # 快取一小時，避免重複消耗 API 額度
def get_cleaned_data(token, start_date, end_date):
    api.login_by_token(api_token=token)
    
    # 1. 抓取期貨日K (作為找 ATM 的基準)
    df_fut = api.taiwan_futures_daily(
        futures_id='TX', start_date=start_date, end_date=end_date
    )
    
    # 2. 抓取選擇權日行情 (這部分資料量極大，建議依日期分段抓取或只抓月選)
    # 這裡示範邏輯：清洗出「月選」、距離結算 > 20 天的合約
    df_opt = api.taiwan_option_daily(
        option_id='TXO', start_date=start_date, end_date=end_date
    )
    
    # 清洗：只留收盤價、履約價、買賣權、到期月份
    df_opt = df_opt[['date', 'strike_price', 'type', 'settlement_price', 'contract_date']]
    
    return df_fut, df_opt

def find_atm_contract(current_fut_price, df_opt_today, target_type, min_days=20):
    """
    動態對齊 ATM 邏輯：
    1. 計算每個合約距離結算的天數
    2. 篩選 > 20 天的合約
    3. 找出 strike_price 離 current_fut_price 最近的一檔
    """
    # 轉換日期格式
    df_opt_today['contract_date'] = pd.to_datetime(df_opt_today['contract_date'])
    today = pd.to_datetime(df_opt_today['date'].iloc[0])
    
    # 篩選遠期合約 (至少20天)
    df_far = df_opt_today[(df_opt_today['contract_date'] - today).dt.days >= min_days]
    
    # 篩選 Call 或 Put
    df_side = df_far[df_far['type'] == target_type]
    
    # 尋找 ATM (履約價與期貨現價差值絕對值最小者)
    idx = (df_side['strike_price'] - current_fut_price).abs().idxmin()
    return df_side.loc[idx]
