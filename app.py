import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="實時收益儀表板", layout="wide")

# 1. 初始化網頁記憶體 (Session State) 用來儲存使用者的動態資產配置
if 'portfolio' not in st.session_state:
    # 預設幫你帶入你先前的真實持股作為初始範本，你隨時可以在網頁上修改或刪除它們！
    st.session_state.portfolio = {
        '2887.TW': 4570,   # 台新新光金
        '6757.TW': 1000,   # 台灣虎航
        '8069.TWO': 200,   # 元太
        '1773.TW': 100,    # 勝一
        '3293.TWO': 20,    # 鈊象
        '2412.TW': 10      # 中華電
    }

st.title("🚀 實時收益儀表板")
st.caption("這是一個完全由網頁即時驅動、零資料庫的動態量化投資組合看板。")

# ================= 區塊一：投資組合自主管理中心 =================
st.markdown("---")
st.subheader("🛠️ 持股動態管理後台")

col_in1, col_in2, col_btn = st.columns([3, 2, 2])
with col_in1:
    input_ticker = st.text_input("輸入股票代號 (上市加 .TW / 上櫃加 .TWO，如：2330.TW, NVDA)：", "").upper().strip()
with col_in2:
    input_shares = st.number_input("輸入持有股數：", min_value=1, value=1000, step=100)
with col_btn:
    st.write("") # 排版對齊用
    st.write("")
    if st.button("➕ 新增 / 更新持股配置"):
        if input_ticker:
            st.session_state.portfolio[input_ticker] = input_shares
            st.toast(f"成功加入/更新 {input_ticker} 共 {input_shares:,} 股！")
            st.rerun()

# 渲染目前持股的標籤與刪除按鈕
if st.session_state.portfolio:
    st.markdown("#### 📋 目前投資組合內容")
    # 每行顯示 3 檔股票的管理介面
    portfolio_items = list(st.session_state.portfolio.items())
    for i in range(0, len(portfolio_items), 3):
        cols = st.columns(3)
        for j, (ticker, shares) in enumerate(portfolio_items[i:i+3]):
            with cols[j]:
                # 建立一個乾淨的管理小列
                st.write(f"🔹 **{ticker}** : {shares:,} 股")
                if st.button(f"❌ 刪除 {ticker}", key=f"del_{ticker}"):
                    del st.session_state.portfolio[ticker]
                    st.rerun()
else:
    st.info("💡 目前投資組合內沒有任何股票，請在上方輸入代號與股數來建立你的資產配置！")


# ================= 區塊二：即時金融數據抓取與量化計算 =================
if st.session_state.portfolio:
    st.markdown("---")
    tickers = list(st.session_state.portfolio.keys())
    
    try:
        with st.spinner("正在跟 Yahoo Finance 即時同步行情並現場進行 1 年期歷史回測..."):
            # 抓取報價數據
            raw_latest = yf.download(tickers, period="5d")['Close']
            raw_hist = yf.download(tickers, period="1y")['Close']
            
            # 補值防呆機制
            raw_latest = raw_latest.ffill().bfill()
            raw_hist = raw_hist.ffill().bfill()
            
            # 防呆型別轉換：確保單檔股票與多檔股票在 Pandas 裡面的結構一致
            if len(tickers) == 1:
                df_latest_close = pd.DataFrame({tickers[0]: raw_latest})
                df_hist_close = pd.DataFrame({tickers[0]: raw_hist})
            else:
                df_latest_close = raw_latest
                df_hist_close = raw_hist
                
            # 提取最新市價與昨日收盤價
            latest_prices = df_latest_close.iloc[-1].to_dict()
            prev_prices = df_latest_close.iloc[-2].to_dict() if len(df_latest_close) > 1 else latest_prices
            
            # 計算當前總市值
            portfolio_values = {}
            total_market_value = 0
            for t in tickers:
                shares = st.session_state.portfolio[t]
                price = latest_prices[t]
                val = shares * price
                portfolio_values[t] = val
                total_market_value += val
                
            # 計算即時配置權重
            weights = {t: portfolio_values[t] / total_market_value for t in tickers}
            
            # 建立最新行情表 DataFrame
            latest_rows = []
            for t in tickers:
                shares = st.session_state.portfolio[t]
                price = latest_prices[t]
                prev_price = prev_prices[t]
                daily_chg = ((price - prev_price) / prev_price) * 100
                
                latest_rows.append({
                    '代號': t,
                    '配置權重 (%)': weights[t] * 100,
                    '當前價格': price,
                    '今日漲跌幅 (%)': daily_chg,
                    '持有股數': shares,
                    '持股市值': portfolio_values[t]
                })
            df_latest_summary = pd.DataFrame(latest_rows)
            
            # 現場進行動態歷史投資組合回測
            daily_returns = df_hist_close.pct_change(fill_method=None).fillna(0)
            portfolio_daily_return = pd.Series(0, index=daily_returns.index)
            for t in tickers:
                portfolio_daily_return += daily_returns[t] * weights[t]
                
            portfolio_cum_return = (1 + portfolio_daily_return).cumprod() - 1
            df_history_plot = pd.DataFrame({'portfolio_return': portfolio_cum_return}).reset_index()
            df_history_plot['Date'] = df_history_plot['Date'].dt.strftime('%Y-%m-%d')
            
        # ================= 區塊三：大面板數據渲染 =================
        total_return_pct = df_history_plot['portfolio_return'].iloc[-1] * 100
        avg_daily_chg = df_latest_summary['今日漲跌幅 (%)'].mean()
        
        # 頂部三大指標
        col1, col2, col3 = st.columns(3)
        col1.metric("歷史累積報酬率 (現場回測)", f"{total_return_pct:.2f} %")
        col2.metric("成分股今日平均漲跌", f"{avg_daily_chg:.2f} %")
        col3.metric("目前資產總市值", f"${total_market_value:,.2f}")
        
        st.markdown("---")
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.subheader("📈 組合淨值累積走勢 (過去一年)")
            fig_line = px.line(df_history_plot, x='Date', y='portfolio_return', title="動態回測績效曲線")
            fig_line.update_traces(line_color='#00CC96', line_width=2.5)
            st.plotly_chart(fig_line, use_container_width=True)
            
        with right_col:
            st.subheader("🍕 即時戰略資產權重")
            fig_pie = px.pie(df_latest_summary, values='配置權重 (%)', names='代號', title='即時配置權重比重')
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        st.markdown("---")
        st.subheader("🔍 核心持股最新行情與資產估值")
        
        st.dataframe(df_latest_summary.style.format({
            '配置權重 (%)': '{:.1f}%', '當前價格': '${:.2f}', '今日漲跌幅 (%)': '{:+.2f}%',
            '持有股數': '{:,}', '持股市值': '${:,.2f}'
        }).highlight_max(axis=0, subset=['今日漲跌幅 (%)'], color='#D4EDDA'), use_container_width=True)
        
    except Exception as e:
        st.error(f"即時處理您的投資組合時發生錯誤（請確認股票代號是否正確，例如美股 NVDA、台股 2330.TW）：{e}")
