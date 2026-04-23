def train_rolling_model(df, train_window=100, test_window=20):
    df = df.copy()
    # 強制將欄位名稱轉小寫，防止 KeyError
    df.columns = [c.lower() for c in df.columns]
    
    # 計算指標
    df['rsi'] = ta.rsi(df['close'], length=14)
    # 加上判斷，如果真的沒 high/low 就跳過威廉指標，避免崩潰
    if 'high' in df.columns and 'low' in df.columns:
        df['willr'] = ta.willr(df['high'], df['low'], df['close'], length=14)
    else:
        df['willr'] = df['rsi'] # 墊檔用，防止後面報錯
        
    df['ema_fast'] = ta.ema(df['close'], length=12)
    df['ema_slow'] = ta.ema(df['close'], length=26)
    # ... 剩下的代碼不變 ...
