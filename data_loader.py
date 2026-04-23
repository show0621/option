import streamlit as st
from FinMind.data import DataLoader
import pandas as pd

api = DataLoader()

@st.cache_data(ttl=3600)
def get_cleaned_data(start_date, end_date):
    try:
        token = st.secrets["FINMIND_TOKEN"]
        api.login_by_token(api_token=token)
    except:
        return None, None

    df_fut = api.taiwan_futures_daily(futures_id='TX', start_date=start_date, end_date=end_date)
    # 將日期設為索引方便 merge
    if not df_fut.empty:
        df_fut['date'] = pd.to_datetime(df_fut['date'])
        df_fut.set_index('date', inplace=True)

    df_opt = api.taiwan_option_daily(option_id='TXO', start_date=start_date, end_date=end_date)
    return df_fut, df_opt
