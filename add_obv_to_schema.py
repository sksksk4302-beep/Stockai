import json

# 스키마 파일 읽기
with open('schema/stock_daily_schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

# OBV 필드 정의
obv_field = {
    "name": "obv",
    "type": "FLOAT",
    "mode": "NULLABLE",
    "description": "On-Balance Volume"
}

# ATR 필드 찾기
atr_index = None
for i, field in enumerate(schema):
    if field['name'] == 'atr':
        atr_index = i
        break

if atr_index is not None:
    # OBV가 이미 있는지 확인
    obv_exists = any(field['name'] == 'obv' for field in schema)
    if not obv_exists:
        schema.insert(atr_index + 1, obv_field)
        print("[OK] OBV field added after ATR.")
    else:
        print("[WARN] OBV field already exists.")
else:
    print("[ERROR] ATR field not found.")

# 스키마 파일 저장
with open('schema/stock_daily_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=4, ensure_ascii=False)

print(f"[OK] Schema updated. Total {len(schema)} fields")
