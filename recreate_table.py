"""
BigQuery 테이블 재생성 스크립트
기존 테이블을 삭제하고 새 스키마로 재생성합니다.
"""
from bigquery_client import BigQueryClient

def recreate_table():
    bq = BigQueryClient()
    
    # 1. 기존 테이블 삭제
    try:
        bq.client.delete_table(bq.table_id)
        print(f"✅ 기존 테이블 삭제 완료: {bq.table_id}")
    except Exception as e:
        print(f"⚠️ 테이블 삭제 중 오류 (무시 가능): {e}")
    
    # 2. 데이터셋 생성 (이미 있으면 무시)
    bq.create_dataset_if_not_exists()
    
    # 3. 새 스키마로 테이블 생성
    bq.create_table_if_not_exists()
    
    print(f"✅ 새 테이블 생성 완료: {bq.table_id}")
    print("📊 새 스키마가 적용되었습니다!")

if __name__ == "__main__":
    recreate_table()
