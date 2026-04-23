import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt=None, initial_capital=100000):
    """
    台指期 60K 共振精準回測 + 選擇權(價平 Delta=0.5) 損益推算
    """
    df_60k = df_60k.copy()
    
    # 1. 確保時間格式精準 (保留 10:00, 11:00 等盤中時間)
    try:
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date']) + pd.Timedelta(hours=8)
            df_60k.set_index('date', inplace=True)
        elif not isinstance(df_60k.index, pd.DatetimeIndex):
            df_60k.index = pd.to_datetime(df_60k.index) + pd.Timedelta(hours=8)
    except:
        pass

    # 2. 指標計算與日線趨勢對齊 (用昨日收盤對齊今日盤中)
    df_60k = df_60k.sort_index()
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    
    df_daily = df_60k.resample('D').last().dropna()
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # 3. 買進訊號定義
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # 4. 模擬回測迴圈 (以期貨盤中精準點位進出)
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        # 進場：使用盤中真實的期貨價格
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp}
        
        # 出場：盤中即時跌破/突破就出場
        elif active_pos:
            is_exit = False
            if active_pos["type"] == "BC" and row['close'] < row['ema20']:
                is_exit = True
            elif active_pos["type"] == "BP" and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                # 計算期貨真實賺賠的點數
                pnl_points = (row['close'] - active_pos['entry_p']) if active_pos["type"] == "BC" else (active_pos['entry_p'] - row['close'])
                
                # === 關鍵：推算選擇權的真實損益 ===
                # 假設買進價平(ATM)，Delta 約為 0.5。期貨賺 100 點，選擇權大約賺 50 點。
                # 假設進場時的價平權利金約為 150 點 (這裡用固定概算，你實戰時以當時報價為準)
                est_opt_points = pnl_points * 0.5 
                assumed_opt_premium = 150 
                
                opt_pnl_pct = (est_opt_points / assumed_opt_premium) * 100
                balance += est_opt_points * 50 # 選擇權一口跳動 50 元
                
                trade_logs.append({
                    "進場時間": active_pos["time"],
                    "出場時間": timestamp,
                    "類型": active_pos["type"],
                    "期貨進場價": round(active_pos['entry_p'], 2),
                    "期貨出場價": round(row['close'], 2),
                    "大盤價差": round(pnl_points, 2),
                    "預估選擇權點數": round(est_opt_points, 2), # Delta 0.5 推算
                    "損益%": round(opt_pnl_pct, 2),
                    "帳戶餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
