def backtest_engine(df_fut, df_opt, ai_results, initial_capital=20000):
    balance = initial_capital
    position = None # 儲存當前持有的選擇權資訊
    history = []

    for i in range(len(df_fut)):
        current_date = df_fut.iloc[i]['date']
        fut_close = df_fut.iloc[i]['close']
        
        # --- 檢查出場 ---
        if position:
            # 從 df_opt 找今日該合約報價
            today_opt_price = df_opt[(df_opt['date'] == current_date) & 
                                     (df_opt['strike_price'] == position['strike']) &
                                     (df_opt['type'] == position['type'])]['settlement_price'].values
            
            if len(today_opt_price) > 0:
                pnl_pct = (today_opt_price[0] - position['entry_price']) / position['entry_price']
                days_held = (pd.to_datetime(current_date) - pd.to_datetime(position['entry_date'])).days
                
                # 執行規則：獲利 50/100%, 損失 50%, 盤整 3 天
                if pnl_pct >= 1.0 or pnl_pct >= 0.5 or pnl_pct <= -0.5 or days_held >= 3:
                    balance += (today_opt_price[0] * 50) # 選擇權一點 50 元
                    history.append({"exit_date": current_date, "pnl": pnl_pct})
                    position = None # 平倉

        # --- 檢查進場 (多時框共振 + AI 機率) ---
        ai_signal = ai_results[ai_results['date'] == current_date]
        if not position and not ai_signal.empty:
            prob = ai_signal['ai_prob'].values[0]
            resonation = ai_signal['resonation'].values[0] # 預先算好的 30/60/D 共振
            
            if resonation and prob > 0.75:
                # 呼叫 ATM 對齊邏輯
                opt_today = df_opt[df_opt['date'] == current_date]
                target_side = "Call" if ai_signal['prediction'] == 1 else "Put"
                
                try:
                    target_opt = find_atm_contract(fut_close, opt_today, target_side)
                    position = {
                        "entry_date": current_date,
                        "strike": target_opt['strike_price'],
                        "type": target_side,
                        "entry_price": target_opt['settlement_price']
                    }
                    balance -= (target_opt['settlement_price'] * 50)
                except:
                    continue # 若當日無符合 20 天之合約則跳過

    return pd.DataFrame(history), balance
