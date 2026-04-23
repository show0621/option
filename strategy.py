import pandas as pd
import pandas_ta as ta
import streamlit as st

def run_backtest(df_60k, df_opt=None, initial_capital=100000):
    """
    台指期 60K 共振精準回測 + 選擇權買方特性 (含 50% 停損與歸零保護)
    """
    df_60k = df_60k.copy()
    
    # 1. 時間格式處理
    try:
        if 'date' in df_60k.columns:
            df_60k['date'] = pd.to_datetime(df_60k['date']) + pd.Timedelta(hours=8)
            df_60k.set_index('date', inplace=True)
        elif not isinstance(df_60k.index, pd.DatetimeIndex):
            df_60k.index = pd.to_datetime(df_60k.index) + pd.Timedelta(hours=8)
    except:
        pass

    # 2. 指標計算與日線對齊
    df_60k = df_60k.sort_index()
    df_60k['ema20'] = ta.ema(df_60k['close'], length=20)
    
    df_daily = df_60k.resample('D').last().dropna()
    df_daily['ema20_d'] = ta.ema(df_daily['close'], length=20)
    
    df_daily['trend_d'] = 0
    df_daily.loc[df_daily['close'] > df_daily['ema20_d'], 'trend_d'] = 1
    df_daily.loc[df_daily['close'] < df_daily['ema20_d'], 'trend_d'] = -1
    
    daily_trend_map = df_daily['trend_d'].shift(1).to_dict()
    df_60k['daily_filter'] = df_60k.index.normalize().map(daily_trend_map)

    # 3. 買進訊號定義
    df_60k['buy_call_signal'] = (df_60k['close'] > df_60k['ema20']) & (df_60k['daily_filter'] == 1)
    df_60k['buy_put_signal'] = (df_60k['close'] < df_60k['ema20']) & (df_60k['daily_filter'] == -1)

    # 4. 回測迴圈
    balance = initial_capital
    trade_logs = []
    active_pos = None

    # --- 參數設定 ---
    assumed_premium = 150   # 假設買進價平選擇權花費 150 點
    stop_loss_pct = 0.50    # 停損設定：虧損達 50% 就砍倉

    for timestamp, row in df_60k.iterrows():
        # A. 進場邏輯
        if active_pos is None:
            if row['buy_call_signal']:
                active_pos = {"type": "BC", "entry_p": row['close'], "time": timestamp, "premium": assumed_premium}
            elif row['buy_put_signal']:
                active_pos = {"type": "BP", "entry_p": row['close'], "time": timestamp, "premium": assumed_premium}
        
        # B. 出場與停損邏輯
        elif active_pos:
            # 即時計算這根 K 棒的期貨價差
            current_pnl_points = (row['close'] - active_pos['entry_p']) if active_pos["type"] == "BC" else (active_pos['entry_p'] - row['close'])
            # 推算選擇權目前損益 (Delta 0.5)
            current_opt_pnl = current_pnl_points * 0.5
            
            is_exit = False
            exit_reason = ""
            final_opt_pnl = 0
            
            # --- 🛡️ 條件 1：50% 強制停損 ---
            max_loss_allowed = active_pos['premium'] * stop_loss_pct
            
            if current_opt_pnl <= -max_loss_allowed:
                is_exit = True
                exit_reason = "50% 停損"
                final_opt_pnl = -max_loss_allowed # 結算就是固定虧一半

            # --- 🛡️ 條件 2：策略指標跌破均線 ---
            elif active_pos["type"] == "BC" and row['close'] < row['ema20']:
                is_exit = True
                exit_reason = "均線反轉出場"
                final_opt_pnl = current_opt_pnl
            elif active_pos["type"] == "BP" and row['close'] > row['ema20']:
                is_exit = True
                exit_reason = "均線反轉出場"
                final_opt_pnl = current_opt_pnl
            
            # 執行出場結算
            if is_exit:
                # --- 🛡️ 條件 3：買方保護 (最慘就是歸零) ---
                if final_opt_pnl < -active_pos['premium']:
                    final_opt_pnl = -active_pos['premium']
                    exit_reason = "跳空歸零"
                
                # 計算最終報酬率
                opt_pnl_pct = (final_opt_pnl / active_pos['premium']) * 100
                balance += final_opt_pnl * 50 # 選擇權一口跳動 50 元
                
                trade_logs.append({
                    "進場時間": active_pos["time"],
                    "出場時間": timestamp,
                    "類型": active_pos["type"],
                    "期貨進場價": round(active_pos['entry_p'], 2),
                    "期貨出場價": round(row['close'], 2),
                    "出場原因": exit_reason,             # ✨ 新增：讓你知道是怎麼出場的
                    "預估選擇權點數": round(final_opt_pnl, 2),
                    "損益%": round(opt_pnl_pct, 2),
                    "帳戶餘額": int(balance)
                })
                active_pos = None

    return pd.DataFrame(trade_logs), balance
