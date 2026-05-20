import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine

st.set_page_config(page_title="台美 AI 雙擎基金監控後台", layout="wide")

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
    st.dataframe(styled_df.style.format({
        '配置權重 (%)': '{:.1f}%', '當前價格': '${:.2f}', '今日漲跌幅 (%)': '{:+.2f}%'
    }).highlight_max(axis=0, columns=['今日漲跌幅 (%)'], color='#D4EDDA'), use_container_width=True)

except Exception as e:
    st.error(f"請等待資料庫初始化或確認連線設定。")
