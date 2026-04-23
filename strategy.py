import pandas as pd
import pandas_ta as ta
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime

# --- 1. 計算多時框共振信號 ---
def calculate_momentum_resonation(df_30k, df_60k, df_daily):
    """
    計算三個時框的 RSI，判斷是否共振一致
    """
    # 確保數據包含 RSI
    df_30k['rsi'] = ta.rsi(df_30k['close'], length=14)
    df_60k['rsi'] = ta.rsi(df_60k['close'], length=14)
    df_daily['rsi'] = ta.rsi(df_daily['close'], length=14)
    
    # 取最後一筆訊號 (實務上回測需對齊時間戳)
    # 這裡回傳一個布林值：True 代表多頭共振, False 代表空頭共振
    bullish = (df_30k['rsi'].iloc[-1] > 50) and (df_60k['rsi'].iloc[-1] > 50) and (df_daily['rsi'].iloc[-1] > 50)
    bearish = (df_30k['rsi'].iloc[-1] < 50) and (df_60k['rsi'].iloc[-1] < 50) and (df_daily['rsi'].iloc[-1] < 50)
    
    return bullish, bearish

# --- 2. 滾動式訓練 AI 模型 (Rolling Window) ---
def train_rolling_model(df, train_window=250, test_window=20):
    """
    使用 Rolling Window 訓練模型，避免 Overfitting
    df 需包含：close, rsi, mom, volatile 等特徵
    """
    df = df.copy()
    # 特徵工程
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['mom'] = ta.mom(df['close'], length=10)
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int) # 預測下一根漲跌
    df = df.dropna()
    
    features = ['rsi', 'mom']
    all_predictions = []
    
    # 滾動訓練邏輯
    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window].copy()
        
        X_train = train_df[features]
        y_train = train_df['target']
        
        # 建立隨機森林模型
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        # 預測機率
        test_df['ai_prob'] = model.predict_proba(test_df[features])[:, 1]
        test_df['prediction'] = model.predict(test_df[features])
        all_predictions.append(test_df)
        
    return pd.concat(all_predictions) if all_predictions else pd
