import streamlit as st
from strategy import train_rolling_model
import plotly.graph_objects as go

st.set_page_config(page_title="台指選擇權 AI 回測系統")

# --- 側邊欄參數 ---
with st.sidebar:
    api_token = st.text_input("FinMind Token", type="password")
    capital = st.number_input("單筆投入金額", 10000, 30000, 20000)
    prob_threshold = st.slider("AI 進場門檻 (機率)", 0.6, 0.9, 0.75)

# --- 主畫面 ---
st.title("📊 台指期多時框共振 + AI 選擇權策略")

if st.button("開始回測"):
    # 1. 下載資料 (此處簡化處理)
    # df = get_data(api_token, "2023-01-01", "2026-04-23")
    
    # 2. 計算共振信號 (30K/60K/D)
    # 只有當 rsi_30k > 50 & rsi_60k > 50 & rsi_daily > 50 時，resonation = True
    
    # 3. 執行滾動式訓練
    # results = train_rolling_model(df)
    
    # 4. 模擬交易邏輯
    # for row in results:
    #    if resonation and ai_prob > prob_threshold:
    #        if 距離結算 > 20天:
    #            進場買進 ATM Call...
    #            檢查 停利(50%/100%), 停損(50%), 時間(3天)
    
    st.success("回測完成！")
    
    # 5. 繪製損益圖
    fig = go.Figure()
    # fig.add_trace(...)
    st.plotly_chart(fig)
