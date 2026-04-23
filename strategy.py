import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt, initial_capital=100000):
    df_60k = df_60k.copy()
    
    # --- 1. 時間格式與時區修正 (UTC -> 台灣時間) ---
    try:
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date']) + pd.Timedelta(hours=8)
            df_60k.set_index('date', inplace=True)
        else:
            df_60k.index = pd.to_datetime(df_60k.index) + pd.Timedelta(hours=8)
    except:
        pass

    # --- 2. 指標計算與日線趨勢對齊 ---
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_daily = df_60k.resample('D').last().dropna()
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # --- 3. 買進訊號定義 ---
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # --- 4. 模擬月選回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        # A. 進場：尋找月選報價
        if active_pos is None:
            if row['buy_call_signal'] or row['buy_put_signal']:
                opt_type = 'Call' if row['buy_call_signal'] else 'Put'
                # 自動尋找最接近的百位數履約價 (價平)
                strike = round(row['close'] / 100) * 100
                
                # --- 🔑 修正處：將 'strike' 改為 'strike_price' ---
                opt_data = df_opt[
                    (df_opt['date'] == timestamp) & 
                    (df_opt['strike_price'] == strike) & 
                    (df_opt['type'] == opt_type)
                ]
                
                if not opt_data.empty:
                    entry_p = opt_data.iloc[0]['settlement_price']
                    active_pos = {
                        "type": f"Buy {opt_type}", 
                        "strike": strike, 
                        "entry_p": entry_p, 
                        "time": timestamp,
                        "ref_index": row['close'] # 紀錄當時期貨點位做停損參考
                    }

        # B. 出場：共振消失或跌破 EMA20
        elif active_pos:
            is_exit = False
            if "Call" in active_pos['type'] and row['close'] < row['ema20']:
                is_exit = True
            elif "Put" in active_pos['type'] and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                # --- 🔑 修正處：將 'strike' 改為 'strike_price' ---
                exit_opt_data = df_opt[
                    (df_opt['date'] == timestamp) & 
                    (df_opt['strike_price'] == active_pos['strike']) & 
                    (df_opt['type'] == active_pos['type'].split()[1])
                ]
                
                if not exit_opt_data.empty:
                    exit_p = exit_opt_data.iloc[0]['settlement_price']
                    pnl = exit_p - active_pos['entry_p']
                    pnl_pct = (pnl / active_pos['entry_p'] * 100) if active_pos['entry_p'] > 0 else 0
                    
                    balance += pnl * 50 # 選擇權一口也是 50 元
                    
                    trade_logs.append({
                        "進場時間": active_pos["time"],
                        "出場時間": timestamp,
                        "類型": active_pos["type"],
                        "履約價": active_pos["strike"],
                        "權利金進場": active_pos["entry_p"],
                        "權利金出場": exit_p,
                        "損益%": round(pnl_pct, 2),
                        "帳戶餘額": int(balance)
                    })
                    active_pos = None

    return pd.DataFrame(trade_logs), balance
