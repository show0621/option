import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import get_cleaned_data
from strategy import train_rolling_model, run_backtest

# --- 頁面設定 ---
st.set_page_config(page_title="台指選擇權 AI 回測系統", layout="wide")

st.title("📈 台指選擇權 AI 動能回測系統")
st.markdown("""
本系統採用 **30K/60K/日K 多時框動能共振** 策略，結合 **AI 滾動式訓練 (Rolling Window)** 預測多空機率。
""")

# --- 側邊欄：參數設定 ---
with st.sidebar:
    st.header("⚙️ 策略參數")
    # 設定預設回測區間 (至少需一年以上資料供 Rolling Window 訓練)
    start_date = st.date_input("回測開始日期", pd.to_datetime("2023-01-01"))
    end_date = st.date_input("回測結束日期", pd.to_datetime("2026-04-23"))
    
    st.divider()
    capital_min = st.number_input("最低投入資金", value=10000)
    capital_max = st.number_input("最高投入資金", value=30000)
    prob_threshold = st.slider("AI 進場門檻機率", 0.60, 0.95, 0.75, 0.05)
    
    run_btn = st.button("🚀 開始回測", use_container_width=True)

# --- 主程式邏輯 ---
if run_btn:
    with st.spinner("正在從 FinMind 抓取資料並清洗..."):
        df_fut, df_opt = get_cleaned_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
    if df_fut is None or df_fut.empty:
        st.error("期貨資料抓取失敗。")
    elif df_opt is None or df_opt.empty:
        st.error("選擇權資料抓取失敗。")
    else:
        with st.spinner("執行 AI 滾動式訓練 (Rolling Window)..."):
            ai_results = train_rolling_model(df_fut)
            
        with st.spinner("執行回測引擎中..."):
            trade_logs, final_balance = run_backtest(df_fut, df_opt, ai_results)

        # --- 顯示績效指標 ---
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("最終帳戶餘額", f"${final_balance:,.0f}")
        with col2:
            win_rate = (trade_logs['pnl_pct'] > 0).mean() if not trade_logs.empty else 0
            st.metric("勝率", f"{win_rate:.1%}")
        with col3:
            st.metric("總交易次數", len(trade_logs))

        # --- 繪製損益圖 ---
        if not trade_logs.empty:
            st.subheader("📊 累積損益曲線")
            trade_logs['cum_pnl'] = trade_logs['pnl_pct'].add(1).cumprod() * 20000
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trade_logs['exit_date'], y=trade_logs['cum_pnl'], mode='lines+markers', name='帳戶淨值'))
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📜 詳細交易紀錄")
            st.dataframe(trade_logs.style.format({'pnl_pct': '{:.2%}'}), use_container_width=True)
        else:
            st.warning("回測期間內無符合條件的進場訊號。")
