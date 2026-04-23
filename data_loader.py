import streamlit as st
from FinMind.data import DataLoader
import pandas as pd

# 初始化 DataLoader
api = DataLoader()

@st.cache_data(ttl=3600)  # 快取一小時，避免重複消耗 API 額度
def get_cleaned_data(start_date, end_date):
    """
    從 Streamlit Secrets 讀取 Token 並抓取清洗資料
    """
    # 1. 從 Secrets 獲取 Token (請確保已在 Streamlit Cloud 設定好 FINMIND_TOKEN)
    try:
        token = st.secrets["FINMIND_TOKEN"]
        api.login_by_token(api_token=token)
    except Exception as e:
        st.error(f"無法從 Secrets 取得 FinMind Token: {e}")
        return pd.DataFrame(), pd.DataFrame()

    # 2. 抓取期貨日K (作為找 ATM 的基準)
    # 注意：FinMind 回傳欄位通常包含 date, close 等
    df_fut = api.taiwan_futures_daily(
        futures_id='TX', 
        start_date=start_date, 
        end_date=end_date
    )
    
    # 3. 抓取選擇權日行情
    # 注意：此 API 資料量大，回測多年時請觀察記憶體使用狀況
    df_opt = api.taiwan_option_daily(
        option_id='TXO', 
        start_date=start_date, 
        end_date=end_date
    )
    
    # 資料清洗：過濾必要欄位
    # FinMind 欄位名稱若有變動請在此調整 (如 settlement_price 可能是 close)
    df_opt = df_opt[['date', 'strike_price', 'type', 'settlement_price', 'contract_date']]
    
    return df_fut, df_opt

def find_atm_contract(current_fut_price, df_opt_today, target_type, min_days=20):
    """
    動態對齊 ATM 邏輯
    """
    if df_opt_today.empty:
        return None

    # 使用 .copy() 避免 SettingWithCopyWarning
    df = df_opt_today.copy()
    
    # 轉換日期格式
    df['contract_date'] = pd.to_datetime(df['contract_date'])
    today = pd.to_datetime(df['date'].iloc[0])
    
    # 1. 篩選遠期合約 (距離結算日至少 20 天)
    df_far = df[(df['contract_date'] - today).dt.days >= min_days]
    
    if df_far.empty:
        return None
    
    # 2. 篩選 Call 或 Put
    df_side = df_far[df['type'] == target_type]
    
    if df_side.empty:
        return None
    
    # 3. 尋找 ATM (履約價與期貨現價差值絕對值最小者)
    # 找出最小差值的索引
    idx = (df_side['strike_price'] - current_fut_price).abs().idxmin()
    
    return df_side.loc[idx]
