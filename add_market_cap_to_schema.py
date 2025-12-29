import json

# 스키마 파일 읽기
with open('schema/stock_daily_schema.json', 'r', encoding='utf-8') as f:
    schema = json.load(f)

# market_cap 필드 정의
market_cap_field = {
    "name": "market_cap",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Market capitalization"
}

# estimated_eps 필드 찾기 (재무지표 마지막)
estimated_eps_index = None
for i, field in enumerate(schema):
    if field['name'] == 'estimated_eps':
        estimated_eps_index = i
        break

# estimated_eps 다음에 market_cap 추가 (중복 체크)
if estimated_eps_index is not None:
    # market_cap이 이미 있는지 확인
    market_cap_exists = any(field['name'] == 'market_cap' for field in schema)
    if not market_cap_exists:
        schema.insert(estimated_eps_index + 1, market_cap_field)
        print("[OK] market_cap field added after estimated_eps.")
    else:
        print("[WARN] market_cap field already exists.")
else:
    print("[ERROR] estimated_eps field not found.")

# 스키마 파일 저장
with open('schema/stock_daily_schema.json', 'w', encoding='utf-8') as f:
    json.dump(schema, f, indent=4, ensure_ascii=False)

print(f"[OK] Schema updated. Total {len(schema)} fields")
