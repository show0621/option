import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt, initial_capital=100000):
    """
    台指期/選擇權共振回測系統 (最終完成版)
    包含：自動降頻日K、時間格式防護、完整損益計算
    """
    df_60k = df_60k.copy()
    
    # --- 1. 時間格式防護網 (解決 TypeError) ---
    try:
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date'])
            df_60k.set_index('date', inplace=True)
        if not isinstance(df_60k.index, pd.DatetimeIndex):
            df_60k.index = pd.to_datetime(df_60k.index)
    except Exception as e:
        st.error(f"時間格式轉換失敗: {e}")
        return pd.DataFrame(), initial_capital

    df_60k = df_60k.sort_index()

    # --- 2. 自動產生日K 資料 ---
    # 利用 60分K 自動轉成日K，不用再另外餵資料
    df_daily = df_60k.resample('D').last().dropna()
    
    # --- 3. 計算技術指標 ---
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    # --- 4. 趨勢定義與對齊 (核心濾網) ---
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    # 使用昨日的日線趨勢作為今日濾網 (避免未來函數)
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # --- 5. 判斷進場信號 (共振) ---
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # --- 6. 診斷儀表板 (在 Streamlit 顯示執行狀況) ---
    st.write("### 📊 策略引擎診斷")
    c1, c2, c3 = st.columns(3)
    c1.metric("回測起點", str(df_60k.index.min().date()))
    c2.metric("回測終點", str(df_60k.index.max().date()))
    c3.metric("總共振次數", int(df_60k['buy_call_signal'].sum() + df_60k['buy_put_signal'].sum()))

    # --- 7. 模擬回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_pos = None

    for timestamp, row in df_60k.iterrows():
        # A. 尋找進場點
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp}
        
        # B. 檢查出場點與結算
        else:
            is_exit = False
            # 出場邏輯：跌破/突破 60K EMA20 就撤退
            if active_pos["type"] == "BC" and row['close'] < row['ema20']:
                is_exit = True
            elif active_pos["type"] == "BP" and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                # 計算點數損益
                pnl_points = (row['close'] - active_pos['entry_p']) if active_pos["type"] == "BC" else (active_pos['entry_p'] - row['close'])
                
                # 計算損益百分比 (解決 KeyError 的關鍵)
                if active_pos['entry_p'] != 0:
                    pnl_percent = (pnl_points / active_pos['entry_p']) * 100
                else:
                    pnl_percent = 0.0
                
                # 換算為現金 (假設 1 點 = 50 元)
                balance += pnl_points * 50
                
                # 寫入完整交易紀錄
                trade_logs.append({
                    "進場時間": active_pos["time"],
                    "出場時間": timestamp,
                    "類型": active_pos["type"],
                    "進場價": active_pos['entry_p'],
                    "出場價": row['close'],
                    "點數損益": round(pnl_points, 2),
                    "損益%": round(pnl_percent, 2),  # 這個欄位是 app.py 需要的
                    "帳戶餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
