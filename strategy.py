import pandas as pd
import pandas_ta as ta

def prepare_indicators(df_1h):
    df = df_1h.copy()
    # 確保索引是 DateTime 且無時區
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
    df.set_index('date', inplace=True)
    
    # 60K 指標
    df['ema_60k'] = ta.ema(df['close'], length=20)
    
    # 合成日K (EMA 20)
    logic = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}
    df_day = df.resample('D').apply(logic).dropna()
    df_day['ema_day'] = ta.ema(df_day['close'], length=20)
    
    return df, df_day

def run_backtest(df_1h, df_opt):
    df_60k, df_day = prepare_indicators(df_1h)
    
    balance = 100000
    position = None
    logs = []
    
    for date, row in df_60k.iterrows():
        # 強制轉為 string 格式比對，避開時區比對問題
        d_str = date.strftime('%Y-%m-%d')
        
        try:
            current_day_data = df_day.asof(date)
        except: continue

        # --- 出場邏輯 ---
        if position:
            opt_today = df_opt[df_opt['date'].dt.strftime('%Y-%m-%d') == d_str]
            target_opt = opt_today[(opt_today['strike_price'] == position['strike']) & 
                                   (opt_today['type'] == position['type'])]
            
            if not target_opt.empty:
                curr_p = target_opt['settlement_price'].iloc[0]
                pnl = (curr_p - position['entry_price']) / position['entry_price']
                hold_hours = (date - position['entry_date']).total_seconds() / 3600
                
                if pnl >= 0.25 or pnl <= -0.2 or hold_hours >= 4:
                    profit = (curr_p - position['entry_price']) * 50
                    balance += (position['cost'] + profit)
                    logs.append({
                        "進場日期": position['entry_date'],
                        "出場日期": date,
                        "類型": position['type'],
                        "損益%": round(pnl*100, 2),
                        "餘額": balance
                    })
                    position = None

        # --- 進場邏輯 ---
        if not position:
            is_bull = (row['close'] > row['ema_60k']) and (row['close'] > current_day_data['ema_day'])
            is_bear = (row['close'] < row['ema_60k']) and (row['close'] < current_day_data['ema_day'])
            
            if is_bull or is_bear:
                side = "Call" if is_bull else "Put"
                opt_day = df_opt[df_opt['date'].dt.strftime('%Y-%m-%d') == d_str]
                
                if not opt_day.empty:
                    df_side = opt_day[opt_day['type'] == side]
                    if not df_side.empty:
                        idx = (df_side['strike_price'] - row['close']).abs().idxmin()
                        target = df_side.loc[idx]
                        if target['settlement_price'] > 0:
                            cost = target['settlement_price'] * 50
                            balance -= cost
                            position = {
                                "entry_date": date,
                                "strike": target['strike_price'],
                                "type": side,
                                "entry_price": target['settlement_price'],
                                "cost": cost
                            }
                        
    return pd.DataFrame(logs), balance
