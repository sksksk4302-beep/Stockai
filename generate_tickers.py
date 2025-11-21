from pykrx import stock
import json
from datetime import datetime, timedelta
import pandas as pd

def generate_top20_json():
    # Use yesterday's date to ensure data availability
    # If yesterday was weekend, pykrx usually handles it or we might need to go back further.
    # But let's try yesterday (2025-11-20 was likely a weekday if 21 is Friday? 21 is Friday in 2025? 
    # Nov 21 2025 is Friday. So 20 is Thursday. Should be fine.)
    
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    target_date = yesterday.strftime("%Y%m%d")
    
    print(f"Fetching KOSPI market cap for {target_date}...")
    
    try:
        df = stock.get_market_cap_by_ticker(target_date, market="KOSPI")
        
        if df.empty:
            print("Data is empty.")
            return

        print("Columns:", df.columns)
        print("First 5 rows:\n", df.head())
        
        # Ensure numeric
        # '시가총액' might be string if something is wrong, but usually it is int.
        # Let's force it.
        if "시가총액" in df.columns:
            df["시가총액"] = pd.to_numeric(df["시가총액"], errors='coerce')
            
            # Sort by market cap (descending) and take top 20
            df = df.sort_values("시가총액", ascending=False).head(20)
            
            tickers_list = []
            for ticker in df.index:
                name = stock.get_market_ticker_name(ticker)
                tickers_list.append({"code": ticker, "name": name})
            
            with open("tickers.json", "w", encoding="utf-8") as f:
                json.dump(tickers_list, f, ensure_ascii=False, indent=4)
            
            print(f"Successfully created tickers.json with {len(tickers_list)} items.")
            for t in tickers_list:
                print(f"{t['code']}: {t['name']}")
        else:
            print("'시가총액' column not found.")

    except Exception as e:
        print(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_top20_json()
