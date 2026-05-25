import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="實時收益儀表板", layout="wide")
# ...(中間省略)...
st.title("🚀 實時收益儀表板")

@st.cache_resource
def get_db_engine():
    db_url = st.secrets["DATABASE_URL"]
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return create_engine(db_url)

try:
    engine = get_db_engine()
    df_history = pd.read_sql("SELECT * FROM portfolio_history ORDER BY \"Date\" ASC", engine)
    df_latest = pd.read_sql("SELECT * FROM asset_latest", engine)
    
    st.title("🚀 台美 AI 雙擎核心基金 - 實時收益與配置儀表板")
    st.caption(f"數據最後自動更新時間： {df_latest['updated_at'].iloc[0]}")
    
    total_return = df_history['portfolio_return'].iloc[-1] * 100
    avg_daily_chg = df_latest['daily_change_pct'].mean()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("基金歷史累積報酬率", f"{total_return:.2f} %")
    col2.metric("成分股今日平均漲跌", f"{avg_daily_chg:.2f} %")
    col3.metric("監控資產總數", f"{len(df_latest)} 檔持股")
        
    st.markdown("---")
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.subheader("📈 基金淨值累積走勢 (過去一年回測)")
        fig_line = px.line(df_history, x='Date', y='portfolio_return', title="基金動態績效曲線")
        fig_line.update_traces(line_color='#00CC96', line_width=2.5)
        st.plotly_chart(fig_line, use_container_width=True)
        
    with right_col:
        st.subheader("🍕 戰略資產配置權重")
        fig_pie = px.pie(df_latest, values='weight', names='name', title='資產配置比重')
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
        
    st.markdown("---")
    st.subheader("🔍 核心持股最新行情")
    
    styled_df = df_latest[['ticker', 'name', 'market', 'weight', 'current_price', 'daily_change_pct']].copy()
    styled_df.columns = ['代號', '資產名稱', '市場', '配置權重 (%)', '當前價格', '今日漲跌幅 (%)']
    
    # 這裡已經幫你把 columns 改成正確的 subset 了！
    st.dataframe(styled_df.style.format({
        '配置權重 (%)': '{:.1f}%', '當前價格': '${:.2f}', '今日漲跌幅 (%)': '{:+.2f}%'
    }).highlight_max(axis=0, subset=['今日漲跌幅 (%)'], color='#D4EDDA'), use_container_width=True)

except Exception as e:


# === 原本的程式碼在上面 ===
    # except Exception as e:
    #     st.error(f"哎呀！出現了隱藏錯誤：{e}")

    # ========== 新增：即時查詢與買入試算區塊 ==========
    st.markdown("---")
    st.subheader("🛒 潛在投資標的查詢與買入試算")
    
    col_search, col_result = st.columns(2)
    
    with col_search:
        search_ticker = st.text_input("輸入你想關注的股票代號 (如：2330.TW, NVDA, AAPL)：", "")
        simulate_shares = st.number_input("預計購買股數：", min_value=1, value=1000, step=100)
        
    if search_ticker:
        try:
            import yfinance as yf
            # 將輸入的代號轉大寫並即時抓取報價
            ticker_upper = search_ticker.upper()
            t = yf.Ticker(ticker_upper)
            hist = t.history(period="2d")
            
            if not hist.empty:
                latest_p = hist['Close'].iloc[-1]
                prev_p = hist['Close'].iloc[-2] if len(hist) > 1 else latest_p
                chg_pct = ((latest_p - prev_p) / prev_p) * 100
                
                with col_result:
                    st.metric(
                        label=f"🎯 {ticker_upper} 即時報價", 
                        value=f"${latest_p:.2f}", 
                        delta=f"{chg_pct:.2f}%"
                    )
                
                # 聯動計算區
                total_cost = latest_p * simulate_shares
                st.success(f"💡 **買入試算：** 若以當前價格買入 **{simulate_shares:,} 股**，總共需要準備資金 **${total_cost:,.0f}**。")
                st.caption(f"如果你確定要將 {ticker_upper} 納入長期監控，請至後端 GitHub 的 `etl_pipeline.py` 將它加入 ASSETS 字典中！")
                
            else:
                st.warning("抓不到報價，請確認代號是否正確（台股上市請加 .TW，上櫃請加 .TWO）。")
                
        except Exception as e:
            st.error("查詢失敗，請檢查網路或股票代號格式。")
    # 把隱藏的錯誤訊息印出來，這樣萬一以後改錯字才抓得到蟲
    st.error(f"哎呀！出現了隱藏錯誤：{e}")
