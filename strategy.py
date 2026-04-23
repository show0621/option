import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt, initial_capital=100000):
    """
    台指期/選擇權共振回測系統 (強化時間索引版)
    """
    df_60k = df_60k.copy()
    
    # --- 核心修正：確保索引是 DatetimeIndex (解決 TypeError) ---
    try:
        # 如果 'date' 是一欄，先把它轉成時間並設為索引
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date'])
            df_60k.set_index('date', inplace=True)
        # 如果索引本身就是時間字串，直接轉型
        if not isinstance(df_60k.index, pd.DatetimeIndex):
            df_60k.index = pd.to_datetime(df_60k.index)
    except Exception as e:
        st.error(f"時間格式轉換失敗: {e}")
        return pd.DataFrame(), initial_capital

    # 確保資料按時間排序
    df_60k = df_60k.sort_index()

    # --- 1. 自動從 60分K 產生日K 資料 ---
    # 現在 index 是 DatetimeIndex 了，這行就不會噴 TypeError 了
    df_daily = df_60k.resample('D').last().dropna()
    
    # --- 2. 計算技術指標 ---
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    # --- 3. 趨勢定義與對齊 ---
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    # 使用昨日的日線趨勢作為今日濾網
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    # normalize() 是把 09:00:00 變成 00:00:00，方便對齊日線日期
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # --- 4. 判斷進場信號 ---
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # --- 5. 診斷與顯示 ---
    st.write("### 📊 回測執行中...")
    c1, c2, c3 = st.columns(3)
    c1.metric("資料起點", str(df_60k.index.min().date()))
    c2.metric("資料終點", str(df_60k.index.max().date()))
    c3.metric("總共振次數", int(df_60k['buy_call_signal'].sum() + df_60k['buy_put_signal'].sum()))

    # --- 6. 模擬回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp}
        else:
            is_exit = False
            if active_pos["type"] == "BC" and row['close'] < row['ema20']:
                is_exit = True
            elif active_pos["type"] == "BP" and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                pnl = (row['close'] - active_pos['entry_p']) if active_pos["type"] == "BC" else (active_pos['entry_p'] - row['close'])
                balance += pnl * 50
                trade_logs.append({
                    "進場時間": active_pos["time"],
                    "出場時間": timestamp,
                    "類型": active_pos["type"],
                    "點數損益": round(pnl, 2),
                    "帳戶餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
