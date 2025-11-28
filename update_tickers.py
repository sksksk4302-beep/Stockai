from pykrx import stock
import pandas as pd
from datetime import datetime
import json
import os

def update_tickers():
    print("Fetching KOSPI top 100 tickers by market cap...")
    
    # Get today's date or the most recent trading day
    today = datetime.today().strftime("%Y%m%d")
    
    # Fetch market cap data
    try:
        df_cap = stock.get_market_cap_by_ticker(today, market="KOSPI")
    except Exception as e:
        print(f"Error fetching market cap: {e}")
        # Try yesterday if today fails (e.g. weekend or early morning)
        from datetime import timedelta
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        print(f"Retrying with date: {yesterday}")
        df_cap = stock.get_market_cap_by_ticker(yesterday, market="KOSPI")

    # Sort by market cap (descending) and take top 100
    df_cap = df_cap.sort_values("시가총액", ascending=False).head(100)
    
    tickers = []
    for ticker in df_cap.index:
        name = stock.get_market_ticker_name(ticker)
        tickers.append({
            "code": ticker,
            "name": name
        })
        
    print(f"Found {len(tickers)} tickers.")
    
    # Save to tickers.json
    with open('tickers.json', 'w', encoding='utf-8') as f:
        json.dump(tickers, f, indent=4, ensure_ascii=False)
        
    print("✅ tickers.json updated successfully.")

if __name__ == "__main__":
    update_tickers()
