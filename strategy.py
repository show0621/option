import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_daily, df_opt, initial_capital=100000):
    """
    台指期/選擇權共振回測系統
    - df_60k: 60分鐘線資料
    - df_daily: 日線資料
    - df_opt: 選擇權報價資料
    """
    
    # --- 1. 資料預處理 (防止資料型態錯誤) ---
    for df in [df_60k, df_daily]:
        for col in ['open', 'high', 'low', 'close']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df_60k = df_60k.copy().sort_index()
    df_daily = df_daily.copy().sort_index()

    # --- 2. 技術指標計算 ---
    # 60分K 指標
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_60k['rsi'] = ta.rsi(df_60k['close'], length=14)
    
    # 日K 指標
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    # --- 3. 跨時框對齊 (核心邏輯：用前一日的日線趨勢決定今日方向) ---
    # 計算日線趨勢：1 為多頭 (收盤 > EMA), -1 為空頭 (收盤 < EMA)
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    # 將「前一日」的趨勢對齊到 60分K 的日期上 (避免看見未來函數)
    df_60k['date_only'] = df_60k.index.date
    # 建立一個日期對應趨勢的字典，使用 shift(1) 代表今天的 60K 只能參考昨天的日線結果
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k['date_only'].map(daily_trend_map)

    # --- 4. 共振信號定義 ---
    # 多頭共振：60K在EMA之上 且 日線趨勢為多 且 RSI 未過熱(選填)
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    # 空頭共振：60K在EMA之下 且 日線趨勢為空
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # --- 5. 診斷區：為什麼沒信號？ (在介面顯示統計) ---
    st.write("### 🔍 策略診斷數據")
    st.write(f"- 60K 資料總筆數: {len(df_60k)}")
    st.write(f"- 日線多頭天數: {df_daily['trend_d'].value_counts().get(1, 0)}")
    st.write(f"- 符合多頭共振(BC)次數: {df_60k['buy_call_signal'].sum()}")
    st.write(f"- 符合空頭共振(BP)次數: {df_60k['buy_put_signal'].sum()}")

    # --- 6. 模擬回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_position = None
    
    # 為了運算效率，只針對有信號或有部位的時點處理
    for timestamp, row in df_60k.iterrows():
