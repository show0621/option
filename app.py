import streamlit as st
import pandas as pd
from data_loader import get_cleaned_data
from strategy import run_backtest
import plotly.express as px

# 設定網頁標題與佈局
st.set_page_config(page_title="台指期多時框共振系統", layout="wide")
st.title("📈 多時框動能共振回測 (60K + 日K)")

# 側邊欄設定
st.sidebar.header("回測設定")
# 確保 pd 已經定義，日期範圍設定
start_date = st.sidebar.date_input("開始日期", value=pd.to_datetime("2025-01-01"))
end_date = st.sidebar.date_input("結束日期", value=pd.to_datetime("2026-04-23"))

if st.sidebar.button("開始回測"):
    with st.spinner("正在讀取 GitHub 備份資料..."):
        # 呼叫資料讀取函式
        df_fut, df_opt = get_cleaned_data(start_date, end_date)
        
    if df_fut is not None and not df_fut.empty:
        st.success(f"成功載入 {len(df_fut)} 筆數據")
        
        # 執行回測：呼叫 strategy.py 裡的邏輯
        logs_df, final_balance = run_backtest(df_fut, df_opt)
        
        if not logs_df.empty:
            # 顯示結果摘要指標
            st.subheader("🏆 績效總覽")
            col1, col2, col3 = st.columns(3)
            
            total_trades = len(logs_df)
            avg_pnl_pct = logs_df['損益%'].mean()
            
            col1.metric("最終帳戶餘額", f"${final_balance:,.0f}")
            col2.metric("總交易次數", f"{total_trades} 次")
            col3.metric("平均損益%", f"{avg_pnl_pct:.2f}%")
            
            # 繪製權益曲線圖 (已對齊 strategy.py 的欄位：出場時間、帳戶餘額)
            st.subheader("📈 權益曲線 (Equity Curve)")
            fig = px.line(
                logs_df, 
                x="出場時間", 
                y="帳戶餘額", 
                title="選擇權買方共振策略資金曲線",
                markers=True
            )
            fig.update_layout(xaxis_title="時間", yaxis_title="帳戶餘額 (元)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示詳細交易紀錄表
            st.subheader("📝 交易明細表")
            st.dataframe(
                logs_df.style.format({
                    "權利金進場": "{:.2f}",
                    "權利金出場": "{:.2f}",
                    "損益%": "{:.2f}%", 
                    "帳戶餘額": "${:,.0f}" 
                }), 
                use_container_width=True
            )
        else:
            st.warning("⚠️ 在此區間內未發現符合『60K+日K共振』條件的進場點。")
    else:
        st.error("❌ 找不到資料，請確認 GitHub 路徑或檔案是否存在。")
