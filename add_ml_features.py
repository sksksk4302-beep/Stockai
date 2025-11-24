"""
ML 모델용 피처를 스키마에 추가하는 스크립트
Target 변수, Lag Features, Rolling Statistics 추가
"""
import json

# ML 피처 정의
ml_features = [
    # ========== Target 변수 (예측 목표) ==========
    {
        "name": "target_return_1d",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Next 1-day return (%) - PRIMARY TARGET"
    },
    {
        "name": "target_return_3d",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Next 3-day return (%)"
    },
    {
        "name": "target_return_5d",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Next 5-day return (%)"
    },
    {
        "name": "target_close",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Next day close price"
    },
    {
        "name": "target_direction",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Next day direction (1=up, 0=down)"
    },
    {
        "name": "target_high_low_range",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Next day (high-low)/close ratio"
    },
    
    # ========== Lag Features (과거 값) ==========
    # 종가 Lag
    {
        "name": "close_lag1",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Close price 1 day ago"
    },
    {
        "name": "close_lag2",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Close price 2 days ago"
    },
    {
        "name": "close_lag3",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Close price 3 days ago"
    },
    {
        "name": "close_lag5",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Close price 5 days ago"
    },
    
    # 거래량 Lag
    {
        "name": "volume_lag1",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Volume 1 day ago"
    },
    {
        "name": "volume_lag2",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Volume 2 days ago"
    },
    {
        "name": "volume_lag3",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Volume 3 days ago"
    },
    
    # 수익률 Lag
    {
        "name": "return_lag1",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Return 1 day ago (%)"
    },
    {
        "name": "return_lag2",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Return 2 days ago (%)"
    },
    {
        "name": "return_lag3",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Return 3 days ago (%)"
    },
    {
        "name": "return_lag5",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Return 5 days ago (%)"
    },
    
    # 투자자 Lag
    {
        "name": "foreign_net_lag1",
        "type": "BIGINT",
        "mode": "NULLABLE",
        "description": "Foreign net 1 day ago"
    },
    {
        "name": "institution_net_lag1",
        "type": "BIGINT",
        "mode": "NULLABLE",
        "description": "Institution net 1 day ago"
    },
    
    # 변동성 Lag
    {
        "name": "atr_lag1",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "ATR 1 day ago"
    },
    {
        "name": "bb_width_lag1",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "BB width 1 day ago"
    },
    
    # ========== Rolling Statistics (과거 N일 통계) ==========
    # 최근 5일
    {
        "name": "close_5d_min",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Min close in last 5 days"
    },
    {
        "name": "close_5d_max",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Max close in last 5 days"
    },
    {
        "name": "close_5d_std",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Std of close in last 5 days"
    },
    {
        "name": "volume_5d_mean",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Mean volume in last 5 days"
    },
    {
        "name": "volume_5d_std",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Std of volume in last 5 days"
    },
    {
        "name": "return_5d_mean",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Mean return in last 5 days (%)"
    },
    {
        "name": "return_5d_std",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Std of return in last 5 days (volatility)"
    },
    
    # 최근 20일
    {
        "name": "close_20d_min",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Min close in last 20 days"
    },
    {
        "name": "close_20d_max",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Max close in last 20 days"
    },
    {
        "name": "return_20d_sharpe",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Sharpe ratio over last 20 days"
    },
    
    # ========== Price Position (가격 위치) ==========
    {
        "name": "price_vs_ma5",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "(close - ma5) / ma5 (%)"
    },
    {
        "name": "price_vs_ma20",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "(close - ma20) / ma20 (%)"
    },
    {
        "name": "price_vs_ma60",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "(close - ma60) / ma60 (%)"
    },
    {
        "name": "bb_position",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Position in BB (0=lower, 0.5=middle, 1=upper)"
    },
    {
        "name": "rsi_change",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "RSI change from previous day"
    }
]

# 기존 스키마 로드
with open('schema/stock_daily_schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

print(f"기존 필드 수: {len(schema)}")

# ML 피처 추가
schema.extend(ml_features)

print(f"추가 후 필드 수: {len(schema)}")
print(f"추가된 필드 수: {len(ml_features)}")
print(f"\n추가된 카테고리:")
print(f"  - Target 변수: 6개")
print(f"  - Lag Features: 15개")
print(f"  - Rolling Statistics: 10개")
print(f"  - Price Position: 5개")

# 저장
with open('schema/stock_daily_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=4, ensure_ascii=False)

print("\n✅ ML 피처 스키마 업데이트 완료!")
