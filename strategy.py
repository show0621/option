def debug_signals(df_60k):
    st.subheader("🔍 信號診斷報告")
    total_bars = len(df_60k)
    
    # 統計各個條件的達成率
    ema_pass = (df_60k['close'] > df_60k['ema20']).sum()
    daily_pass = (df_60k['trend_d'] == 1).sum()
    both_pass = ((df_60k['close'] > df_60k['ema20']) & (df_60k['trend_d'] == 1)).sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("60K 多頭達成", f"{ema_pass}/{total_bars}")
    col2.metric("日線趨勢多頭達成", f"{daily_pass}/{total_bars}")
    col3.metric("最終共振達成", f"{both_pass}")

    if both_pass == 0:
        st.error("❌ 診斷結果：共振條件完全未達成。請檢查 'trend_d' 欄位是否全為 NaN。")
