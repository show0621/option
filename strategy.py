import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_daily, df_opt, initial_capital=100000):
    """
    台指期/選擇權共振回測系統
    """
    # 確保資料是乾淨的
    df_60k = df_60k.copy()
    df_daily = df_daily.copy()

    # 1. 計算指標
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)

    # 2. 趨勢定義 (日線)
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1

    # 3. 對齊資料 (使用昨日日線趨勢)
    df_60k['date_only'] = df_60k.index.date
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k['date_only'].map(daily_trend_map)

    # 4. 判斷進場信號
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # 5. 回測診斷統計
    st.write("### 📊 回測診斷統計")
    st.write(f"總 K 線筆數: {len(df_60k)}")
    st.write(f"多頭共振信號: {df_60k['buy_call_signal'].sum()} 次")
    st.write(f"空頭共振信號: {df_60k['buy_put_signal'].sum()} 次")

    # 6. 模擬交易迴圈
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        # 如果目前沒倉位
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp}
        
        # 如果目前有倉位，判斷平倉 (跌破/突破 EMA20)
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
                    "目前餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
