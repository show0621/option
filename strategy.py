import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
import numpy as np

def train_rolling_model(df, train_window=120, test_window=20):
    """
    使用滾動窗口訓練 AI 模型
    train_window: 訓練用的天數 (約半年)
    test_window: 預測的天數 (約一個月)
    """
    df = df.copy()
    # 1. 強制欄位名稱轉小寫，防止 KeyError
    df.columns = [c.lower() for c in df.columns]
    
    # 2. 計算技術指標 (增加模型判斷維度)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema_fast'] = ta.ema(df['close'], length=12)
    df['ema_slow'] = ta.ema(df['close'], length=26)
    
    # 確保有 high/low 才能算威廉指標，否則用 rsi 代替
    if 'high' in df.columns and 'low' in df.columns:
        df['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14)
    else:
        df['willr'] = df['rsi']
        
    # 3. 定義標籤：下一日收盤價是否上漲
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)
    df = df.dropna()
    
    features = ['rsi', 'willr', 'ema_fast', 'ema_slow']
    all_preds = []
    
    # 4. 滾動訓練邏輯
    if len(df) < (train_window + test_window):
        return pd.DataFrame()

    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window].copy()
        
        # 簡單隨機森林模型
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(train_df[features], train_df['target'])
        
        # 取得上漲機率
        test_df['ai_prob'] = model.predict_proba(test_df[features])[:, 1]
        all_preds.append(test_df)
        
    return pd.concat(all_preds) if all_preds else pd.DataFrame()

def run_backtest(df_fut, df_opt, ai_results, threshold=0.55):
    """
    回測邏輯：根據 AI 訊號買入 ATM 選擇權
    """
    balance = 100000  # 初始假設資金 (點數換算)
    position = None
    logs = []
    
    # 統一期貨欄位
    df_fut.columns = [c.lower() for c in df_fut.columns]
    
    # 合併 AI 預測
    df_main = df_fut.merge(ai_results[['ai_prob']], left_index=True, right_index=True, how='inner')

    for date, row in df_main.iterrows():
        # --- A. 出場邏輯 (平倉) ---
        if position:
            today_opt = df_opt[df_opt['date'] == date]
            target_opt = today_opt[(today_opt['strike_price'] == position['strike']) & 
                                   (today_opt['type'] == position['type'])]
            
            if not target_opt.empty:
                curr_p = target_opt['settlement_price'].iloc[0]
                pnl_pct = (curr_p - position['entry_price']) / position['entry_price']
                
                # 停損停利條件：獲利 30% 或 損失 25% 或 持倉超過 3 天
                hold_days = (date - position['entry_date']).days
                if pnl_pct >= 0.3 or pnl_pct <= -0.25 or hold_days >= 3:
                    profit = (curr_p - position['entry_price']) * 50  # 1 點 50 元
                    balance += (position['cost'] + profit)
                    logs.append({
                        "進場日期": position['entry_date'],
                        "出場日期": date,
                        "類型": position['type'],
                        "履約價": position['strike'],
                        "損益%
