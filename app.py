import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_loader import get_cleaned_data
from strategy import train_rolling_model, run_backtest

# --- 頁面設定 ---
st.set_page_config(page_title="台指選擇權 AI 動能回測系統", layout="wide")

st.title("📈 台指選擇權 AI 動能回測系統")
st.markdown("""
本系統採用 **30K/60K/日K 多時框動能共振** 策略，結合 **AI 滾動式訓練 (Rolling Window)** 預測多空機率。
進場邏輯：多時框共振 + AI 機率 > 75% 買進離結算 > 20 天之 ATM 合約。
""")

# --- 側邊欄：參數設定 ---
with st.sidebar:
    st.header("⚙️ 策略參數")
    start_date = st.date_input("回測開始日期", pd.to_datetime("2023-01-01"))
    end_date = st.date_input("回測結束日期", pd.to_datetime("2026-04-23"))
    
    st.divider()
    capital_min = st.number_input("最低投入資金", value=10000)
    capital_max = st.number_input("最高投入資金", value=30000)
    prob_threshold = st.slider("AI 進場門檻機率", 0.60, 0.95, 0.75, 0.05)
    
    run_btn = st.button("🚀 開始回測", use_container_width=True)

# --- 主程式邏輯 ---
if run_btn:
    with st.spinner("正在從 FinMind 抓取資料並進行數據清洗..."):
        # 1. 獲取資料 (自動從 Secrets 讀取 Token)
        df_fut, df_opt = get_cleaned_data(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
        
    if df_fut.empty or df_opt.empty:
        st.error("資料抓取失敗，請檢查 FinMind Token 是否正確設定於 Secrets 中。")
    else:
        with st.spinner("正在進行 AI 滾動式模型訓練 (Rolling Window)..."):
            # 2. 執行 AI 訓練
            ai_results = train_rolling_model(df_fut)
            
        with st.spinner("執行回測引擎中..."):
            # 3. 執行回測
            trade_logs, final_balance = run_backtest(
                df_fut, df_opt, ai_results, 
                capital_range=(capital_min, capital_max)
            )

        # --- 顯示結果 ---
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("最終帳戶餘額", f"${final_balance:,.0f}")
        with col2:
            win_rate = (trade_logs['pnl_pct'] > 0).mean() if not trade_logs.empty else 0
            st.metric("勝率", f"{win_rate:.1%}")
        with col3:
            total_trades = len(trade_logs)
            st.metric("總交易
