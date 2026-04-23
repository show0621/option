import numpy as np
from sklearn.ensemble import RandomForestClassifier

def train_rolling_model(df, train_window=250, test_window=20):
    """
    df: 包含技術指標的 dataframe
    train_window: 250天 (約一年交易日)
    test_window: 20天 (約一月交易日)
    """
    signals = []
    
    # 特徵工程：假設已計算好 30K/60K/D 的 RSI
    features = ['rsi_30k', 'rsi_60k', 'rsi_daily']
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int) # 預測下一根漲跌
    
    for i in range(train_window, len(df) - test_window, test_window):
        train_df = df.iloc[i-train_window : i]
        test_df = df.iloc[i : i+test_window]
        
        X_train = train_df[features]
        y_train = train_df['target']
        
        # 訓練 AI 模型 (隨機森林)
        model = RandomForestClassifier(n_estimators=100)
        model.fit(X_train, y_train)
        
        # 預測並存入機率
        probs = model.predict_proba(test_df[features])[:, 1]
        test_df['ai_prob'] = probs
        signals.append(test_df)
        
    return pd.concat(signals)
