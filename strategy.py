import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier

def train_rolling_model(df, train_window=100, test_window=20):
    df = df.copy()
    # 增加更多技術指標，讓 AI 更好抓到動能
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14)
    df['ema_fast'] = ta.ema(df['close'], length=12)
    df['ema_slow'] = ta.ema(df['close'], length=26)
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    
    features = ['rsi', 'willr', 'ema_fast', 'ema_slow']
    all_preds = []
    
    # 縮短訓練窗口至 100 天，讓訊號更早出現
    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window].copy()
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(train_df[features], train_df['target'])
        
        test_df['ai_prob'] = model.predict_proba(test_df[features])[:, 1]
        test_df['prediction'] = model.predict(test_df[features])
        all_preds.append(test_df)
        
    return pd.concat(all_preds) if all_preds else pd.DataFrame()

def run_backtest(df_fut, df_opt, ai_results):
    balance = 20000 # 初始資金
    position = None
    logs = []
    
    # 合併 AI 預測結果
    df_main = df_fut.merge(ai_results[['ai_prob', 'prediction']], left_index=True, right_index=True, how='inner')

    for date, row in df_main.iterrows():
        # --- 1. 出場邏輯 ---
        if position:
            today_opt = df_opt[df_opt['date'] == date]
            target_opt = today_opt[(today_opt['strike_price'] == position['strike']) & 
                                   (today_opt['type'] == position['type'])]
            
            if not target_opt.empty:
                curr_p = target_opt['settlement_price'].iloc[0]
                pnl_pct = (curr_p - position['entry_price']) / position['entry_price']
                
                # 停損停利：利潤 > 30% 或 損失 < -30% 或 持倉超過 5 天
                hold_days = (date - position['entry_date']).days
                if pnl_pct >= 0.3 or pnl_pct <= -0.3 or hold_days >= 5:
                    profit = (curr_p - position['entry_price']) * 50 * position['lots']
                    balance += (position['cost'] + profit)
                    logs.append({
                        "entry_date": position['entry_date'],
                        "exit_date": date,
                        "type": position['type'],
                        "pnl_pct": pnl_pct,
                        "balance": balance
                    })
                    position = None

        # --- 2. 進場邏輯 (放寬門檻) ---
        # 只要機率 > 0.55 就進場，且目前沒持倉
        if not position and row['ai_prob'] > 0.55:
            side = "Call" if row['ai_prob'] > 0.5 else "Put"
            opt_date_df = df_opt[df_opt['date'] == date]
            
            if not opt_date_df.empty:
                # 尋找價平 (ATM) 合約
                df_side = opt_date_df[opt_date_df['type'] == side]
                if not df_side.empty:
                    # 找到最接近期貨現價的履約價
                    idx = (df_side['strike_price'] - row['close']).abs().idxmin()
                    target_opt = df_side.loc[idx]
                    
                    cost = target_opt['settlement_price'] * 50
                    if balance >= cost and cost > 0:
                        balance -= cost
                        position = {
                            "entry_date": date,
                            "strike": target_opt['strike_price'],
                            "type": side,
                            "entry_price": target_opt['settlement_price'],
                            "lots": 1,
                            "cost": cost
                        }
                        
    return pd.DataFrame(logs), balance
