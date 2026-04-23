import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def train_rolling_model(df, train_window=250, test_window=20):
    df = df.copy()
    # 簡單特徵工程
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['mom'] = ta.mom(df['close'], length=10)
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    
    features = ['rsi', 'mom']
    all_preds = []
    
    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window].copy()
        
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(train_df[features], train_df['target'])
        
        test_df['ai_prob'] = model.predict_proba(test_df[features])[:, 1]
        test_df['prediction'] = model.predict(test_df[features])
        all_preds.append(test_df)
        
    return pd.concat(all_preds) if all_preds else pd.DataFrame()

def run_backtest(df_fut, df_opt, ai_results):
    balance = 20000
    position = None
    logs = []
    
    df_main = df_fut.merge(ai_results[['ai_prob', 'prediction']], left_index=True, right_index=True, how='left')

    for date, row in df_main.iterrows():
        # 出場邏輯 (TP 50%/100%, SL 50%, Time 3 Days)
        if position:
            today_opt = df_opt[(df_opt['date'] == date.strftime('%Y-%m-%d')) & 
                               (df_opt['strike_price'] == position['strike']) & 
                               (df_opt['type'] == position['type'])]
            if not today_opt.empty:
                curr_p = today_opt['settlement_price'].iloc[0]
                pnl_pct = (curr_p - position['entry_price']) / position['entry_price']
                hold_days = (date - position['entry_date']).days
                
                if pnl_pct >= 0.5 or pnl_pct <= -0.5 or hold_days >= 3:
                    profit = (curr_p - position['entry_price']) * 50 * position['lots']
                    balance += (position['cost'] + profit)
                    logs.append({"exit_date": date, "pnl_pct": pnl_pct, "type": position['type']})
                    position = None

        # 進場邏輯
        if not position and row['ai_prob'] > 0.75:
            opt_date_df = df_opt[df_opt['date'] == date.strftime('%Y-%m-%d')]
            if not opt_date_df.empty:
                # 簡單找 ATM：篩選與 close 最接近的 strike
                side = "Call" if row['prediction'] == 1 else "Put"
                df_side = opt_date_df[opt_date_df['type'] == side]
                if not df_side.empty:
                    target_opt = df_side.loc[(df_side['strike_price'] - row['close']).abs().idxmin()]
                    cost = target_opt['settlement_price'] * 50
                    if balance >= cost:
                        balance -= cost
                        position = {"entry_date": date, "strike": target_opt['strike_price'], 
                                    "type": side, "entry_price": target_opt['settlement_price'], 
                                    "lots": 1, "cost": cost}
    return pd.DataFrame(logs), balance
