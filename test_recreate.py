"""
BigQuery 테이블 재생성 테스트 스크립트
"""
import sys
import traceback
from bigquery_client import BigQueryClient

def main():
    try:
        print("✅ BigQueryClient import 성공")
        bq = BigQueryClient()
        print("✅ BigQueryClient 인스턴스 생성 성공")

        # 테이블 삭제 시도 (존재하면)
        try:
            bq.client.delete_table(bq.table_id)
            print(f"✅ 기존 테이블 삭제 완료: {bq.table_id}")
        except Exception as e:
            print(f"⚠️ 테이블 삭제 중 오류 (무시 가능): {e}")

        # 데이터셋 및 테이블 생성
        bq.create_dataset_if_not_exists()
        print("✅ 데이터셋 확인/생성 완료")
        bq.create_table_if_not_exists()
        print(f"✅ 새 테이블 생성 완료: {bq.table_id}")

        print("\n🎉 테이블 재생성 성공!")
    except Exception as e:
        print("\n❌ 에러 발생:")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
