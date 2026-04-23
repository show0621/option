from FinMind.data import DataLoader
import pandas as pd

def get_data(token, start_date, end_date):
    api = DataLoader()
    api.login_by_token(api_token=token)
    
    # 獲取台指期日K、60K、30K (範例以日K為主，多時框需重複調用)
    # 產品代碼範例: 'TX' (大台)
    df_futures = api.taiwan_futures_daily(
        futures_id='TX',
        start_date=start_date,
        end_date=end_date
    )
    
    # 獲取選擇權報價 (回測用，這部分資料量非常大，實務上需逐日抓取)
    # df_opt = api.taiwan_option_daily(...)
    
    return df_futures
