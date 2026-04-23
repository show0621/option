import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt, initial_capital=100000):
    """
    台指期/選擇權共振回測系統 (自動計算日K趨勢版)
    - df_60k: 60分鐘線資料 (包含日期時間索引)
    - df_opt: 選擇權報價資料
    """
    # 確保資料格式正確
    df_60k = df_60k.copy().sort_index()
    
    # --- 1. 自動從 60分K 產生日K 資料 ---
    # 這樣你就不用在 app.py 另外抓日線資料了
    df_daily = df_60k.resample('D').last().dropna()
    
    # --- 2. 計算技術指標 ---
    # 60分K 指標
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    
    # 日K 指標
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    # --- 3. 趨勢定義與對齊 ---
    # 日線趨勢：收盤 > EMA 為 1, 反之為 -1
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    # 使用昨日的日線趨勢作為今日濾網
    df_60k['date_only'] = df_60k.index.date
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # --- 4. 判斷進場信號 ---
    # 多頭共振：(60K > EMA) 且 (日K 趨勢向上)
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    # 空頭共振：(60K < EMA) 且 (日K 趨勢向下)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # --- 5. 診斷與顯示 ---
    st.write("### 📊 回測診斷數據 (Resonance Check)")
    c1, c2, c3 = st.columns(3)
    c1.metric("60K 總筆數", len(df_60k))
    c2.metric("多頭共振信號", int(df_60k['buy_call_signal'].sum()))
    c3.metric("空頭共振信號", int(df_60k['buy_put_signal'].sum()))

    # --- 6. 模擬回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        # 進場邏輯
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp}
        
        # 出場邏輯 (跌破或突破 EMA20)
        else:
            is_exit = False
            if active_pos["type"] == "BC" and row['close'] < row['ema20']:
                is_exit = True
            elif active_pos["type"] == "BP" and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                pnl = (row['close'] - active_pos['entry_p']) if active_pos["type"] == "BC" else (active_pos['entry_p'] - row['close'])
                # 簡單計算損益 (點數 * 50)
                balance += pnl * 50
                trade_logs.append({
                    "進場時間": active_pos["time"],
                    "出場時間": timestamp,
                    "類型": active_pos["type"],
                    "點數損益": round(pnl, 2),
                    "目前餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
