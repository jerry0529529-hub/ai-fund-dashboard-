import os
import yfinance as yf
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine

# 1. 這裡以後只要輸入你真實的「股數 (shares)」即可
ASSETS = {
    '2887.TW': {'name': '台新新光金', 'shares': 4570, 'market': 'TW'},
    '6757.TW': {'name': '台灣虎航', 'shares': 1000, 'market': 'TW'},
    '8069.TWO': {'name': '元太', 'shares': 200, 'market': 'TW'},
    '1773.TW': {'name': '勝一', 'shares': 100, 'market': 'TW'},
    '3293.TWO': {'name': '鈊象', 'shares': 20, 'market': 'TW'},
    '2412.TW': {'name': '中華電', 'shares': 10, 'market': 'TW'}
}

# 2. 自動將股數轉換為權重的魔法區塊 (讓後續的 ETL 程式不會出錯)
try:
    import yfinance as yf
    tickers = list(ASSETS.keys())
    # 偷偷去抓今天的最新價格
    latest_data = yf.download(tickers, period="5d")['Close']
    latest_prices = latest_data.ffill().iloc[-1]
    
    # 計算總市值
    total_value = sum(ASSETS[t]['shares'] * latest_prices[t] for t in tickers)
    
    # 自動算出百分比權重，並補回 ASSETS 字典裡給原程式使用
    for t in tickers:
        ASSETS[t]['weight'] = float((ASSETS[t]['shares'] * latest_prices[t]) / total_value)
except Exception as e:
    print(f"自動計算權重時發生錯誤: {e}")
def run_etl():
    print(f"[{datetime.now()}] 啟動 ETL 資料管道...")
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("未偵測到 DATABASE_URL 環境變數！")
    
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
    engine = create_engine(DATABASE_URL)
    tickers = list(ASSETS.keys())
    data = yf.download(tickers, period="1y")['Close']
    data = data.ffill().bfill()
    
   daily_returns = data.pct_change(fill_method=None).fillna(0)
    portfolio_daily_return = pd.Series(0, index=daily_returns.index)
    for ticker, info in ASSETS.items():
        portfolio_daily_return += daily_returns[ticker] * info['weight']
        
    portfolio_cum_return = (1 + portfolio_daily_return).cumprod() - 1
    history_df.index.name = 'Date'
history_df = history_df.reset_index()

    latest_rows = []
    for ticker, info in ASSETS.items():
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) >= 2:
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            daily_chg = ((current_price - prev_price) / prev_price) * 100
        else:
            current_price = t.info.get('regularMarketPrice', 0)
            daily_chg = t.info.get('regularMarketChangePercent', 0)
            
        latest_rows.append({
            'ticker': ticker,
            'name': info['name'],
            'market': info['market'],
            'weight': info['weight'] * 100,
            'current_price': round(current_price, 2),
            'daily_change_pct': round(daily_chg, 2),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    latest_df = pd.DataFrame(latest_rows)
    history_df.to_sql('portfolio_history', engine, if_exists='replace', index=False)
    latest_df.to_sql('asset_latest', engine, if_exists='replace', index=False)
    print("ETL 執行成功，資料已同步至雲端資料庫。")

if __name__ == "__main__":
    run_etl()
