import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt, initial_capital=100000):
    df_60k = df_60k.copy()
    df_opt = df_opt.copy()
    
    # --- 1. 時間格式與時區修正 (60分K) ---
    try:
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date']) + pd.Timedelta(hours=8)
            df_60k.set_index('date', inplace=True)
        elif not isinstance(df_60k.index, pd.DatetimeIndex):
            df_60k.index = pd.to_datetime(df_60k.index) + pd.Timedelta(hours=8)
    except:
        pass

    # --- 👑 2. 選擇權資料庫「強效對齊」處理 ---
    try:
        # 將選擇權時間統一去掉時分秒，只保留日期 (normalize)
        df_opt['date'] = pd.to_datetime(df_opt['date']).dt.normalize()
        # 確保履約價是數字格式
        df_opt['strike_price'] = pd.to_numeric(df_opt['strike_price'], errors='coerce')
        # 確保 Type 統一包含 'Call' 或 'Put' (解決大小寫或前後空白問題)
        df_opt['type'] = df_opt['type'].astype(str).str.strip().str.capitalize()
    except Exception as e:
        st.error(f"選擇權資料預處理異常: {e}")

    # --- 3. 指標計算與日線趨勢對齊 ---
    df_60k = df_60k.sort_index()
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    
    df_daily = df_60k.resample('D').last().dropna()
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # --- 4. 買進訊號定義 ---
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # 在 Streamlit 顯示到底觸發了多少次訊號
    st.write("### 📊 策略引擎內部診斷")
    st.write(f"- 期貨共振訊號觸發次數：{int(df_60k['buy_call_signal'].sum() + df_60k['buy_put_signal'].sum())} 次")
    
    # --- 5. 模擬月選回測迴圈 ---
    balance = initial_capital
    trade_logs = []
    active_pos = None
    matched_trades = 0 # 計算成功找到選擇權報價的次數

    for timestamp, row in df_60k.iterrows():
        # A. 進場：尋找月選報價
        if active_pos is None:
            if row['buy_call_signal'] or row['buy_put_signal']:
                opt_type = 'Call' if row['buy_call_signal'] else 'Put'
                strike = round(row['close'] / 100) * 100
                
                # 將期貨訊號時間去尾數，只留日期去跟 df_opt 對齊
                target_date = pd.to_datetime(timestamp).normalize()
                
                # 精準搜尋
                opt_data = df_opt[
                    (df_opt['date'] == target_date) & 
                    (df_opt['strike_price'] == strike) & 
                    (df_opt['type'].str.contains(opt_type, case=False, na=False))
                ]
                
                if not opt_data.empty:
                    # 如果同一天有多個月分合約，優先選近月 (假設有 contract_date 欄位)
                    if 'contract_date' in opt_data.columns:
                        opt_data = opt_data.sort_values('contract_date')
                        
                    entry_p = opt_data.iloc[0]['settlement_price']
                    
                    # 避免抓到 0 元或空值的極端報價
                    if pd.notna(entry_p) and entry_p > 0:
                        active_pos = {
                            "type": f"Buy {opt_type}", 
                            "strike": strike, 
                            "entry_p": entry_p, 
                            "time": timestamp,
                            "entry_date": target_date 
                        }
                        matched_trades += 1

        # B. 出場：共振消失或跌破/突破 EMA20
        elif active_pos:
            is_exit = False
            if "Call" in active_pos['type'] and row['close'] < row['ema20']:
                is_exit = True
            elif "Put" in active_pos['type'] and row['close'] > row['ema20']:
                is_exit = True
            
            if is_exit:
                exit_target_date = pd.to_datetime(timestamp).normalize()
                opt_type_str = active_pos['type'].split()[1] # 取得 Call 或 Put
                
                exit_opt_data = df_opt[
                    (df_opt['date'] == exit_target_date) & 
                    (df_opt['strike_price'] == active_pos['strike']) & 
                    (df_opt['type'].str.contains(opt_type_str, case=False, na=False))
                ]
                
                if not exit_opt_data.empty:
                    if 'contract_date' in exit_opt_data.columns:
                        exit_opt_data = exit_opt_data.sort_values('contract_date')
                        
                    exit_p = exit_opt_data.iloc[0]['settlement_price']
                    
                    if pd.notna(exit_p) and exit_p > 0:
                        pnl = exit_p - active_pos['entry_p']
                        pnl_pct = (pnl / active_pos['entry_p'] * 100) if active_pos['entry_p'] > 0 else 0
                        
                        balance += pnl * 50 # 選擇權一口跳動 50 元
                        
                        trade_logs.append({
                            "進場時間": active_pos["time"],
                            "出場時間": timestamp,
                            "類型": active_pos["type"],
                            "履約價": active_pos["strike"],
                            "權利金進場": active_pos["entry_p"],
                            "權利金出場": exit_p,
                            "點數損益": round(pnl, 2),
                            "損益%": round(pnl_pct, 2),
                            "帳戶餘額": int(balance)
                        })
                        active_pos = None
                else:
                    # 如果出場那天剛好沒抓到報價，為了避免卡單，強制用隔天或忽略 (這裡先直接平倉解鎖)
                    active_pos = None 

    st.write(f"- 成功匹配到選擇權報價進場次數：{matched_trades} 次")
    
    return pd.DataFrame(trade_logs), balance
