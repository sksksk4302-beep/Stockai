"""
Test script to verify data collection and feature engineering
"""
import sys
sys.path.insert(0, '.')

from main import fetch_one_ticker
from datetime import datetime, timedelta
import pandas as pd

# Test with Samsung Electronics
ticker = "005930"
end = datetime.today()
start = end - timedelta(days=30)

print(f"Testing data collection for {ticker}")
print(f"Period: {start.date()} to {end.date()}")

try:
    df = fetch_one_ticker(ticker, start, end)
    
    print(f"\n✅ Data collected: {len(df)} rows")
    print(f"\n📊 Columns ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}: {df[col].dtype}")
    
    print(f"\n🔍 Sample data (first row):")
    print(df.head(1).T)
    
    print(f"\n⚠️ Null counts:")
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        print(null_cols)
    else:
        print("  No null values")
    
    # Check for required columns
    required_cols = ['date', 'ticker', 'name', 'close']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"\n❌ Missing required columns: {missing}")
    else:
        print(f"\n✅ All required columns present")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
