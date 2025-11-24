"""
스키마에 파생 피처를 추가하는 스크립트
"""
import json

# 파생 피처 정의
derived_features = [
    {
        "name": "day_of_week",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Day of week (0=Monday, 4=Friday)"
    },
    {
        "name": "week_of_month",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Week number within month (1-5)"
    },
    {
        "name": "month",
        "type": "INTEGER",
        "mode": "NULLABLE",
        "description": "Month (1-12)"
    },
    {
        "name": "is_month_end",
        "type": "BOOLEAN",
        "mode": "NULLABLE",
        "description": "Is last trading day of month"
    },
    {
        "name": "return_vs_kospi",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Return difference vs KOSPI (%)"
    },
    {
        "name": "price_range",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Daily price range (high-low)/close"
    },
    {
        "name": "upper_shadow",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Upper shadow ratio (upper wick)"
    },
    {
        "name": "lower_shadow",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Lower shadow ratio (lower wick)"
    },
    {
        "name": "body_ratio",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Candle body ratio |open-close|/close"
    },
    {
        "name": "volume_ratio",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Volume / 20-day average"
    },
    {
        "name": "foreign_participation",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Foreign net / trading value (%)"
    },
    {
        "name": "institutional_participation",
        "type": "FLOAT",
        "mode": "NULLABLE",
        "description": "Institutional net / trading value (%)"
    }
]

# 기존 스키마 로드
with open('schema/stock_daily_schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

print(f"기존 필드 수: {len(schema)}")

# 파생 피처 추가
schema.extend(derived_features)

print(f"추가 후 필드 수: {len(schema)}")
print(f"추가된 필드: {[f['name'] for f in derived_features]}")

# 저장
with open('schema/stock_daily_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=4, ensure_ascii=False)

print("✅ 스키마 파일 업데이트 완료!")
