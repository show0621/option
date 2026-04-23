import pandas as pd
import pandas_ta as ta

def run_backtest(df_60k, df_daily, df_opt, initial_capital=100000):
    """
    df_60k: 60分鐘線資料 (需包含 open, high, low, close)
    df_daily: 日線資料 (用於判斷大趨勢共振)
    df_opt: 選擇權報價資料 (FinMind 抓取的 TXO Data)
    """
    # 1. 計算技術指標
    df_60k = df_60k.copy()
    df_daily = df_daily.copy()
    
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    # 2. 將日線趨勢標記到 60K 資料中 (確保 60K 抓到的是『當下』已知的日線趨勢)
    # 我們將日線資料的日期往後移一天，代表當天開盤時能參考的最新的日線
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1  # 多頭
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1 # 空頭
    
    # 對齊日期：將日線趨勢 merge 到 60K
    df_60k['date_only'] = df_60k.index.date
    daily_trend_map = df_daily['trend_d'].shift(1) # 重要：用前一天的日線決定今天趨勢
    df_60k = df_60k.join(daily_trend_map, on='date_only', rsuffix='_daily')

    # 3. 定義共振條件
    # 多頭共振：(60K 收盤 > 60K EMA20) 且 (前日日K > 日 EMA20)
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['trend_d'] == 1)
    # 空頭共振：(60K 收盤 < 60K EMA20) 且 (前日日K < 日 EMA20)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['trend_d'] == -1)

    # 4. 回測邏輯
    balance = initial_capital
    trade_logs = []
    active_position = None

    for timestamp, row in df_60k.iterrows():
        # 簡單邏輯：出現信號進場，隔天或收盤出場 (孟霖可再自行定義停利損)
        if active_position is None:
            if row['buy_call_signal']:
                # 進場買 Call：這裡需要去 df_opt 找最接近當下點位的價外一檔週選
                active_position = {"type": "BC", "entry_price": row['close'], "entry_time": timestamp}
            elif row['buy_put_signal']:
                active_position = {"type": "BP", "entry_price": row['close'], "entry_time": timestamp}
        
        # 簡單平倉邏輯：共振消失即平倉
        elif active_position:
            is_exit = False
            if active_position['type'] == "BC" and row['close'] < row['ema20']:
                is_exit = True
            elif active_position['type'] == "BP" and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                pnl = (row['close'] - active_position['entry_price']) if active_position['type'] == "BC" else (active_position['entry_price'] - row['close'])
                # 換算成選擇權點數 (這裡先簡化用期貨點數示意，實際需算 Delta)
                profit = pnl * 50 
                balance += profit
                trade_logs.append({
                    "進場時間": active_position['entry_time'],
                    "出場時間": timestamp,
                    "類型": active_position['type'],
                    "損益點數": pnl,
                    "餘額": balance
                })
                active_position = None

    return pd.DataFrame(trade_logs), balance
