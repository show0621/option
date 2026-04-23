import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
import numpy as np

def train_rolling_model(df, train_window=120, test_window=20):
    df = df.copy()
    # 統一小寫欄位
    df.columns = [c.lower() for c in df.columns]
    
    # 計算指標
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema_fast'] = ta.ema(df['close'], length=12)
    df['ema_slow'] = ta.ema(df['close'], length=26)
    
    if 'high' in df.columns and 'low' in df.columns:
        df['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14)
    else:
        df['willr'] = df['rsi']
        
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    
    features = ['rsi', 'willr', 'ema_fast', 'ema_slow']
    all_preds = []
    
    if len(df) < (train_window + test_window):
        return pd.DataFrame()

    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window].copy()
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(train_df[features], train_df['target'])
        
        test_df['ai_prob'] = model.predict_proba(test_df[features])[:, 1]
        all_preds.append(test_df)
        
    return pd.concat(all_preds) if all_preds else pd.DataFrame()

def run_backtest(df_fut, df_opt, ai_results, threshold=0.55):
    balance = 100000
    position = None
    logs = []
    
    df_fut.columns = [c.lower() for c in df_fut.columns]
    df_main = df_fut.merge(ai_results[['ai_prob']], left_index=True, right_index=True, how='inner')

    for date, row in df_main.iterrows():
        if position:
            today_opt = df_opt[df_opt['date'] == date]
            target_opt = today_opt[(today_opt['strike_price'] == position['strike']) & 
                                   (today_opt['type'] == position['type'])]
            
            if not target_opt.empty:
                curr_p = target_opt['settlement_price'].iloc[0]
                pnl_pct = (curr_p - position['entry_price']) / position['entry_price']
                
                hold_days = (date - position['entry_date']).days
                if pnl_pct >= 0.3 or pnl_pct <= -0.25 or hold_days >= 3:
                    profit = (curr_p - position['entry_price']) * 50
                    balance += (position['cost'] + profit)
                    logs.append({
                        "進場日期": position['entry_date'],
                        "出場日期": date,
                        "類型": position['type'],
                        "履約價": position['strike'],
                        "損益%": round(pnl_pct * 100, 2),
                        "餘額": balance
                    })
                    position = None

        if not position:
            is_call = row['ai_prob'] >= threshold
            is_put = row['ai_prob'] <= (1 - threshold)
            
            if is_call or is_put:
                side = "Call" if is_call else "Put"
                opt_date_df = df_opt[df_opt['date'] == date]
                
                if not opt_date_df.empty:
                    df_side = opt_date_df[opt_date_df['type'] == side]
                    if not df_side.empty:
                        idx = (df_side['strike_price'] - row['close']).abs().idxmin()
                        target_opt = df_side.loc[idx]
                        entry_price = target_opt['settlement_price']
                        if entry_price > 0:
                            cost = entry_price * 50
                            balance -= cost
                            position = {
                                "entry_date": date,
                                "strike": target_opt['strike_price'],
                                "type": side,
                                "entry_price": entry_price,
                                "cost": cost
                            }
                        
    return pd.DataFrame(logs), balance
