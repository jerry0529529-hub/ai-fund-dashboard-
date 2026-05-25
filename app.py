import streamlit as st
import pandas as pd
import plotly.express as px
import yfinance as yf

st.set_page_config(page_title="實時收益儀表板", layout="wide")

# --- 🌟 新增：自動抓取並記憶公司名稱的快取魔法函數 ---
@st.cache_data
def get_company_name(ticker):
    try:
        info = yf.Ticker(ticker).info
        # 優先抓簡稱，沒有就抓全名，如果都抓不到就退回顯示代號
        name = info.get('shortName') or info.get('longName') or ticker
        return name
    except:
        return ticker
# ---------------------------------------------------

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {
        '2887.TW': 4570,
        '6757.TW': 1000,
        '8069.TWO': 200,
        '1773.TW': 100,
        '3293.TWO': 20,
        '2412.TW': 10
    }

st.title("🚀 實時收益儀表板")
st.caption("這是一個完全由網頁即時驅動、零資料庫的多幣別動態量化投資組合看板。")

# ================= 區塊一：投資組合自主管理中心 =================
st.markdown("---")
st.subheader("🛠️ 持股動態管理後台")

col_in1, col_in2, col_btn = st.columns([3, 2, 2])
with col_in1:
    input_ticker = st.text_input("輸入股票代號 (台股加 .TW / .TWO，美股直打 NVDA)：", "").upper().strip()
with col_in2:
    input_shares = st.number_input("輸入持有股數：", min_value=1, value=1000, step=100)
with col_btn:
    st.write("") 
    st.write("")
    if st.button("➕ 新增 / 更新持股配置"):
        if input_ticker:
            st.session_state.portfolio[input_ticker] = input_shares
            c_name = get_company_name(input_ticker)
            st.toast(f"成功加入 {c_name} ({input_ticker}) 共 {input_shares:,} 股！")
            st.rerun()

if st.session_state.portfolio:
    st.markdown("#### 📋 目前投資組合內容")
    portfolio_items = list(st.session_state.portfolio.items())
    for i in range(0, len(portfolio_items), 3):
        cols = st.columns(3)
        for j, (ticker, shares) in enumerate(portfolio_items[i:i+3]):
            with cols[j]:
                c_name = get_company_name(ticker) # 這裡也會顯示公司名稱
                st.write(f"🔹 **{c_name}** ({ticker}) : {shares:,} 股")
                if st.button(f"❌ 刪除 {ticker}", key=f"del_{ticker}"):
                    del st.session_state.portfolio[ticker]
                    st.rerun()
else:
    st.info("💡 目前無任何股票，請在上方建立你的資產配置！")


# ================= 區塊二：多幣別即時數據與匯率換算 =================
if st.session_state.portfolio:
    st.markdown("---")
    tickers = list(st.session_state.portfolio.keys())
    
    try:
        with st.spinner("正在同步跨國行情、擷取公司名稱，並進行回測..."):
            
            fx_ticker = yf.Ticker("USDTWD=X")
            fx_data = fx_ticker.history(period="5d")
            usd_to_twd = float(fx_data['Close'].iloc[-1])
            
            raw_latest = yf.download(tickers, period="5d")['Close']
            raw_hist = yf.download(tickers, period="1y")['Close']
            
            raw_latest = raw_latest.ffill().bfill()
            raw_hist = raw_hist.ffill().bfill()
            
            if len(tickers) == 1:
                df_latest_close = pd.DataFrame({tickers[0]: raw_latest})
                df_hist_close = pd.DataFrame({tickers[0]: raw_hist})
            else:
                df_latest_close = raw_latest
                df_hist_close = raw_hist
                
            latest_prices = df_latest_close.iloc[-1].to_dict()
            prev_prices = df_latest_close.iloc[-2].to_dict() if len(df_latest_close) > 1 else latest_prices
            
            portfolio_values_twd = {}
            total_market_value_twd = 0
            latest_rows = []
            
            for t in tickers:
                shares = st.session_state.portfolio[t]
                raw_price = latest_prices[t]
                prev_price = prev_prices[t]
                daily_chg = ((raw_price - prev_price) / prev_price) * 100
                c_name = get_company_name(t) # 取得公司名稱
                
                if t.endswith('.TW') or t.endswith('.TWO'):
                    currency = "TWD"
                    price_twd = raw_price
                else:
                    currency = "USD"
                    price_twd = raw_price * usd_to_twd
                
                val_twd = shares * price_twd
                portfolio_values_twd[t] = val_twd
                total_market_value_twd += val_twd
                
                latest_rows.append({
                    '代號': t,
                    '公司名稱': c_name, # 寫入資料表
                    '幣別': currency,
                    '原始單價': raw_price,
                    '台幣總市值 (TWD)': val_twd,
                    '今日漲跌幅 (%)': daily_chg,
                    '持有股數': shares
                })
                
            weights = {t: portfolio_values_twd[t] / total_market_value_twd for t in tickers}
            for row in latest_rows:
                row['配置權重 (%)'] = weights[row['代號']] * 100
                
            df_latest_summary = pd.DataFrame(latest_rows)
            
            daily_returns = df_hist_close.pct_change(fill_method=None).fillna(0)
            portfolio_daily_return = pd.Series(0, index=daily_returns.index)
            for t in tickers:
                portfolio_daily_return += daily_returns[t] * weights[t]
                
            portfolio_cum_return = (1 + portfolio_daily_return).cumprod() - 1
            df_history_plot = pd.DataFrame({'portfolio_return': portfolio_cum_return})
            df_history_plot.index.name = 'Date'
            df_history_plot = df_history_plot.reset_index()
            df_history_plot['Date'] = df_history_plot['Date'].dt.strftime('%Y-%m-%d')
            
        # ================= 區塊三：大面板數據渲染 =================
        total_return_pct = df_history_plot['portfolio_return'].iloc[-1] * 100
        avg_daily_chg = df_latest_summary['今日漲跌幅 (%)'].mean()
        
        st.caption(f"💱 系統即時匯率：1 USD = **{usd_to_twd:.2f}** TWD")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("歷史累積報酬率 (現場回測)", f"{total_return_pct:.2f} %")
        col2.metric("成分股今日平均漲跌", f"{avg_daily_chg:.2f} %")
        col3.metric("目前資產總市值 (台幣)", f"NT$ {total_market_value_twd:,.0f}")
        
        st.markdown("---")
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.subheader("📈 組合淨值累積走勢 (過去一年)")
            fig_line = px.line(df_history_plot, x='Date', y='portfolio_return', title="動態回測績效曲線")
            fig_line.update_traces(line_color='#00CC96', line_width=2.5)
            st.plotly_chart(fig_line, use_container_width=True)
            
        with right_col:
            st.subheader("🍕 即時戰略資產權重")
            # 讓圓餅圖的標籤顯示「公司名稱」
            fig_pie = px.pie(df_latest_summary, values='配置權重 (%)', names='公司名稱', title='即時配置權重比重')
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
            
        st.markdown("---")
        st.subheader("🔍 核心持股最新行情與資產估值")
        
        # 將「公司名稱」加入要顯示的表格欄位中
        display_df = df_latest_summary[['代號', '公司名稱', '幣別', '配置權重 (%)', '原始單價', '今日漲跌幅 (%)', '持有股數', '台幣總市值 (TWD)']]
        
        st.dataframe(display_df.style.format({
            '配置權重 (%)': '{:.1f}%', '原始單價': '{:.2f}', '今日漲跌幅 (%)': '{:+.2f}%',
            '持有股數': '{:,}', '台幣總市值 (TWD)': 'NT$ {:,.0f}'
        }).highlight_max(axis=0, subset=['今日漲跌幅 (%)'], color='#D4EDDA'), use_container_width=True)
        
    except Exception as e:
        st.error(f"處理投資組合時發生錯誤，請確認代號是否正確：{e}")
