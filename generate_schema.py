import json

# Complete schema for stock_daily table with ML features
schema = [
    # Basic fields
    {"name": "date", "type": "DATE", "mode": "REQUIRED", "description": "Trading date"},
    {"name": "ticker", "type": "STRING", "mode": "REQUIRED", "description": "Stock ticker code"},
    {"name": "name", "type": "STRING", "mode": "NULLABLE", "description": "Stock name"},
    
    # OHLCV
    {"name": "open", "type": "INTEGER", "mode": "NULLABLE", "description": "Opening price"},
    {"name": "high", "type": "INTEGER", "mode": "NULLABLE", "description": "High price"},
    {"name": "low", "type": "INTEGER", "mode": "NULLABLE", "description": "Low price"},
    {"name": "close", "type": "INTEGER", "mode": "NULLABLE", "description": "Closing price"},
    {"name": "volume", "type": "INTEGER", "mode": "NULLABLE", "description": "Trading volume"},
    {"name": "close_diff", "type": "INTEGER", "mode": "NULLABLE", "description": "Close price difference from previous day"},
    {"name": "volume_diff", "type": "INTEGER", "mode": "NULLABLE", "description": "Volume difference from previous day"},
    
    # Investor trading
    {"name": "individual_net_buy", "type": "INTEGER", "mode": "NULLABLE", "description": "Individual net buy (10k KRW)"},
    {"name": "foreign_net_buy", "type": "INTEGER", "mode": "NULLABLE", "description": "Foreign net buy (10k KRW)"},
    {"name": "institution_net_buy", "type": "INTEGER", "mode": "NULLABLE", "description": "Institution net buy (10k KRW)"},
    
    # Short selling
    {"name": "short_balance", "type": "INTEGER", "mode": "NULLABLE", "description": "Short balance"},
    {"name": "short_balance_diff", "type": "INTEGER", "mode": "NULLABLE", "description": "Short balance difference"},
    
    # Fundamentals
    {"name": "bps", "type": "FLOAT", "mode": "NULLABLE", "description": "Book value per share"},
    {"name": "per", "type": "FLOAT", "mode": "NULLABLE", "description": "Price to earnings ratio"},
    {"name": "pbr", "type": "FLOAT", "mode": "NULLABLE", "description": "Price to book ratio"},
    {"name": "eps", "type": "FLOAT", "mode": "NULLABLE", "description": "Earnings per share"},
    {"name": "estimated_eps", "type": "FLOAT", "mode": "NULLABLE", "description": "Estimated EPS"},
    
    # Technical indicators - Moving Averages
    {"name": "ma5", "type": "FLOAT", "mode": "NULLABLE", "description": "5-day moving average"},
    {"name": "ma20", "type": "FLOAT", "mode": "NULLABLE", "description": "20-day moving average"},
    {"name": "ma60", "type": "FLOAT", "mode": "NULLABLE", "description": "60-day moving average"},
    {"name": "ma120", "type": "FLOAT", "mode": "NULLABLE", "description": "120-day moving average"},
    
    # RSI
    {"name": "rsi", "type": "FLOAT", "mode": "NULLABLE", "description": "14-day RSI"},
    {"name": "rsi_change", "type": "FLOAT", "mode": "NULLABLE", "description": "RSI change from previous day"},
    
    # Bollinger Bands
    {"name": "bb_upper", "type": "FLOAT", "mode": "NULLABLE", "description": "Bollinger band upper"},
    {"name": "bb_lower", "type": "FLOAT", "mode": "NULLABLE", "description": "Bollinger band lower"},
    {"name": "bb_width", "type": "FLOAT", "mode": "NULLABLE", "description": "Bollinger band width"},
    {"name": "bb_position", "type": "FLOAT", "mode": "NULLABLE", "description": "Position in Bollinger bands (0-1)"},
    
    # ATR
    {"name": "atr", "type": "FLOAT", "mode": "NULLABLE", "description": "14-day Average True Range"},
    
    # Derived features - Date
    {"name": "day_of_week", "type": "INTEGER", "mode": "NULLABLE", "description": "Day of week (0=Monday)"},
    {"name": "month", "type": "INTEGER", "mode": "NULLABLE", "description": "Month (1-12)"},
    {"name": "is_month_end", "type": "BOOLEAN", "mode": "NULLABLE", "description": "Is month end"},
    {"name": "week_of_month", "type": "INTEGER", "mode": "NULLABLE", "description": "Week of month (1-5)"},
    
    # Candle patterns
    {"name": "price_range", "type": "FLOAT", "mode": "NULLABLE", "description": "(high-low)/close"},
    {"name": "body_ratio", "type": "FLOAT", "mode": "NULLABLE", "description": "|open-close|/close"},
    {"name": "upper_shadow", "type": "FLOAT", "mode": "NULLABLE", "description": "Upper shadow ratio"},
    {"name": "lower_shadow", "type": "FLOAT", "mode": "NULLABLE", "description": "Lower shadow ratio"},
    
    # Volume ratio
    {"name": "volume_ratio", "type": "FLOAT", "mode": "NULLABLE", "description": "Volume / 20-day average"},
    
    # Participation
    {"name": "foreign_participation", "type": "FLOAT", "mode": "NULLABLE", "description": "Foreign participation ratio"},
    {"name": "institutional_participation", "type": "FLOAT", "mode": "NULLABLE", "description": "Institutional participation ratio"},
    
    # Lag features - Close
    {"name": "close_lag1", "type": "INTEGER", "mode": "NULLABLE", "description": "Close 1 day ago"},
    {"name": "close_lag2", "type": "INTEGER", "mode": "NULLABLE", "description": "Close 2 days ago"},
    {"name": "close_lag3", "type": "INTEGER", "mode": "NULLABLE", "description": "Close 3 days ago"},
    {"name": "close_lag5", "type": "INTEGER", "mode": "NULLABLE", "description": "Close 5 days ago"},
    
    # Lag features - Volume
    {"name": "volume_lag1", "type": "INTEGER", "mode": "NULLABLE", "description": "Volume 1 day ago"},
    {"name": "volume_lag2", "type": "INTEGER", "mode": "NULLABLE", "description": "Volume 2 days ago"},
    {"name": "volume_lag3", "type": "INTEGER", "mode": "NULLABLE", "description": "Volume 3 days ago"},
    
    # Lag features - Return
    {"name": "return_1d", "type": "FLOAT", "mode": "NULLABLE", "description": "1-day return (%)"},
    {"name": "return_lag1", "type": "FLOAT", "mode": "NULLABLE", "description": "Return 1 day ago"},
    {"name": "return_lag2", "type": "FLOAT", "mode": "NULLABLE", "description": "Return 2 days ago"},
    {"name": "return_lag3", "type": "FLOAT", "mode": "NULLABLE", "description": "Return 3 days ago"},
    {"name": "return_lag5", "type": "FLOAT", "mode": "NULLABLE", "description": "Return 5 days ago"},
    
    # Lag features - Investors
    {"name": "foreign_net_lag1", "type": "INTEGER", "mode": "NULLABLE", "description": "Foreign net 1 day ago"},
    {"name": "institution_net_lag1", "type": "INTEGER", "mode": "NULLABLE", "description": "Institution net 1 day ago"},
    
    # Lag features - Volatility
    {"name": "atr_lag1", "type": "FLOAT", "mode": "NULLABLE", "description": "ATR 1 day ago"},
    {"name": "bb_width_lag1", "type": "FLOAT", "mode": "NULLABLE", "description": "BB width 1 day ago"},
    
    # Rolling statistics - 5 days
    {"name": "close_5d_min", "type": "INTEGER", "mode": "NULLABLE", "description": "Min close in last 5 days"},
    {"name": "close_5d_max", "type": "INTEGER", "mode": "NULLABLE", "description": "Max close in last 5 days"},
    {"name": "close_5d_std", "type": "FLOAT", "mode": "NULLABLE", "description": "Std of close in last 5 days"},
    {"name": "volume_5d_mean", "type": "FLOAT", "mode": "NULLABLE", "description": "Mean volume in last 5 days"},
    {"name": "volume_5d_std", "type": "FLOAT", "mode": "NULLABLE", "description": "Std of volume in last 5 days"},
    {"name": "return_5d_mean", "type": "FLOAT", "mode": "NULLABLE", "description": "Mean return in last 5 days"},
    {"name": "return_5d_std", "type": "FLOAT", "mode": "NULLABLE", "description": "Std of return in last 5 days"},
    
    # Rolling statistics - 20 days
    {"name": "close_20d_min", "type": "INTEGER", "mode": "NULLABLE", "description": "Min close in last 20 days"},
    {"name": "close_20d_max", "type": "INTEGER", "mode": "NULLABLE", "description": "Max close in last 20 days"},
    {"name": "return_20d_sharpe", "type": "FLOAT", "mode": "NULLABLE", "description": "20-day Sharpe ratio"},
    
    # Price position
    {"name": "price_vs_ma5", "type": "FLOAT", "mode": "NULLABLE", "description": "(close - ma5) / ma5 * 100"},
    {"name": "price_vs_ma20", "type": "FLOAT", "mode": "NULLABLE", "description": "(close - ma20) / ma20 * 100"},
    {"name": "price_vs_ma60", "type": "FLOAT", "mode": "NULLABLE", "description": "(close - ma60) / ma60 * 100"},
    {"name": "price_vs_ma120", "type": "FLOAT", "mode": "NULLABLE", "description": "(close - ma120) / ma120 * 100"},
    
    # Target variables
    {"name": "target_return_1d", "type": "FLOAT", "mode": "NULLABLE", "description": "Next 1-day return (%)"},
    {"name": "target_return_3d", "type": "FLOAT", "mode": "NULLABLE", "description": "Next 3-day return (%)"},
    {"name": "target_return_5d", "type": "FLOAT", "mode": "NULLABLE", "description": "Next 5-day return (%)"},
    {"name": "target_close", "type": "INTEGER", "mode": "NULLABLE", "description": "Next day close price"},
    {"name": "target_direction", "type": "INTEGER", "mode": "NULLABLE", "description": "Next day direction (1=up, 0=down)"},
    {"name": "target_high_low_range", "type": "FLOAT", "mode": "NULLABLE", "description": "Next day (high-low)/close ratio"},
]

# Write to file
with open('schema/stock_daily_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=4, ensure_ascii=False)

print(f"✅ Schema file created with {len(schema)} fields")
