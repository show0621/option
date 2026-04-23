import streamlit as st
from data_loader import get_cleaned_data
from strategy import run_backtest
import plotly.express as px

st.set_page_config(page_title="台指期多時框共振系統", layout="wide")
st.title("📈 多時框動能共振回測 (60K + 日K)")

# 側邊欄設定
st.sidebar.header("回測設定")
start_date = st.sidebar.date_input("開始日期", value=pd.to_datetime("2025-01-01"))
end_date = st.sidebar.date_input("結束日期", value=pd.to_datetime("2026-04-23"))

if st.sidebar.button("開始回測"):
    with st.spinner("正在讀取 GitHub 備份資料..."):
        df_fut, df_opt = get_cleaned_data(start_date, end_date)
        
    if df_fut is not None and not df_fut.empty:
        st.success(f"成功載入 {len(df_fut)} 筆小時線數據")
        
        # 執行回測
        logs_df, final_balance = run_backtest(df_fut, df_opt)
        
        if not logs_df.empty:
            # 顯示結果摘要
            col1, col2, col3 = st.columns(3)
            col1.metric("最終餘額", f"${final_balance:,.0f}")
            col2.metric("交易次數", len(logs_df))
            col3.metric("平均損益%", f"{logs_df['損益%'].mean():.2f}%")
            
            # 損益曲線圖
            fig = px.line(logs_df, x="出場日期", y="餘額", title="權益曲線 (Equity Curve)")
            st.plotly_chart(fig, use_container_width=True)
            
            # 交易明細
            st.subheader("交易明細")
            st.dataframe(logs_df.style.format({"損益%": "{:.2f}%", "餘額": "${:,.0f}"}), use_container_width=True)
        else:
            st.warning("在此區間內未發現符合共振條件的進場點。")
    else:
        st.error("找不到期貨資料，請確認檔案已正確上傳至 GitHub。")
