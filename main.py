from pykrx import stock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

try:
    from google.cloud import storage
except ImportError:
    storage = None


# ----------------------------------------
# 1. 코스피 시총 상위 50개 종목 리스트 (Legacy)
# ----------------------------------------
def get_kospi_top50(date: datetime = None) -> pd.DataFrame:
    """
    주어진 날짜 기준 KOSPI 시가총액 상위 50개 티커/종목명/시총을 반환
    """
    if date is None:
        date = datetime.today()
    date_str = date.strftime("%Y%m%d")

    df_cap = stock.get_market_cap_by_ticker(date_str, market="KOSPI")
    df_cap = df_cap.sort_values("시가총액", ascending=False).head(50)

    df_cap = df_cap.reset_index()
    df_cap["종목명"] = df_cap["티커"].apply(stock.get_market_ticker_name)
    return df_cap[["티커", "종목명", "시가총액"]]


# ----------------------------------------
# 2. 개별 종목 한 달치 데이터 수집
# ----------------------------------------
def fetch_one_ticker(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    특정 티커에 대해:
      - 일별 종가, 종가 전일비
      - 거래량, 거래량 전일비
      - 투자자별 매매동향(개인, 외국인, 기관)
      - 공매도잔고(=대차잔고 비슷하게 사용), 전일비
      - 펀더멘털 지표 (PER, EPS, 추정EPS, PBR, BPS)
    를 모두 합쳐서 DataFrame으로 반환
    """
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    # ----- 2-1. 가격/거래량 (OHLCV) -----
    price = stock.get_market_ohlcv_by_date(start_str, end_str, ticker)
    # 필요한 컬럼만 사용
    price = price[["종가", "거래량"]].copy()
    price["종가전일비"] = price["종가"].diff()
    price["거래량전일비"] = price["거래량"].diff()

    # ----- 2-2. 투자자별 매매동향 (순매수 거래대금 기준) -----
    # 컬럼 예: '개인', '외국인', '기관합계', '기타법인', ...
    inv = stock.get_market_trading_value_by_date(start_str, end_str, ticker)

    # 방어적으로 컬럼 체크
    cols = inv.columns
    col_individual = "개인"
    col_foreign = "외국인" if "외국인" in cols else "외국인합계"
    col_institution = "기관합계" if "기관합계" in cols else "기관"

    inv = inv[[col_individual, col_foreign, col_institution]].copy()
    
    # 1만 단위로 나누고 올림 처리
    inv = inv / 10000
    inv = np.ceil(inv)

    inv.columns = ["개인순매수", "외국인순매수", "기관순매수"]

    # ----- 2-3. 공매도 잔고 (대차잔고 유사) -----
    # 공매도잔고, 상장주식수, 공매도금액, 시가총액, 비중
    try:
        short_bal = stock.get_shorting_balance_by_date(start_str, end_str, ticker)
        short_bal = short_bal[["공매도잔고"]].copy()
        short_bal.rename(columns={"공매도잔고": "대차잔고"}, inplace=True)
        short_bal["대차잔고전일비"] = short_bal["대차잔고"].diff()
    except Exception:
        # 일부 종목/기간은 공매도 데이터가 없을 수 있음 → NaN으로 처리
        short_bal = pd.DataFrame(index=price.index)
        short_bal["대차잔고"] = pd.NA
        short_bal["대차잔고전일비"] = pd.NA

    # ----- 2-4. 펀더멘털 지표 (PER, EPS, PBR, BPS, EPS 추정치) -----
    try:
        # get_market_fundamental_by_date: BPS, PER, PBR, EPS, DIV, DPS 제공
        fundamental = stock.get_market_fundamental_by_date(start_str, end_str, ticker)
        
        # 필요한 컬럼만 선택
        fundamental = fundamental[["BPS", "PER", "PBR", "EPS"]].copy()
        
        # 추정 EPS는 pykrx에서 직접 제공하지 않으므로 일단 NULL로 설정
        # 향후 다른 API나 크롤링으로 추가 가능
        fundamental["추정EPS"] = pd.NA
        
    except Exception as e:
        print(f"Warning: Could not fetch fundamental data for {ticker}: {e}")
        # 펀더멘털 데이터가 없는 경우 빈 DataFrame 생성
        fundamental = pd.DataFrame(index=price.index)
        fundamental["BPS"] = pd.NA
        fundamental["PER"] = pd.NA
        fundamental["PBR"] = pd.NA
        fundamental["EPS"] = pd.NA
        fundamental["추정EPS"] = pd.NA

    # ----- 2-5. 데이터 병합 -----
    df = price.join(inv, how="left").join(short_bal, how="left").join(fundamental, how="left")

    df["티커"] = ticker
    df["종목명"] = stock.get_market_ticker_name(ticker)

    # index(날짜)를 컬럼으로
    df = df.reset_index().rename(columns={"index": "날짜"})
    return df



# ----------------------------------------
# 3. 요약 정보 (PER, PBR, 52주 최고/최저)
# ----------------------------------------
def get_ticker_summary(ticker: str) -> dict:
    today = datetime.today()
    today_str = today.strftime("%Y%m%d")
    
    summary = {}
    
    # 3-1. 펀더멘털 (PER, PBR 등)
    try:
        df_fund = stock.get_market_fundamental_by_date(today_str, today_str, ticker)
        if not df_fund.empty:
            # 가장 최근 날짜의 데이터 사용
            row = df_fund.iloc[-1]
            summary["PER"] = row.get("PER", "N/A")
            summary["PBR"] = row.get("PBR", "N/A")
        else:
            summary["PER"] = "N/A"
            summary["PBR"] = "N/A"
    except Exception as e:
        print(f"Error fetching fundamentals: {e}")
        summary["PER"] = "Error"
        summary["PBR"] = "Error"

    # 3-2. 52주 최고/최저 (최근 1년 OHLCV)
    try:
        start_date = (today - timedelta(days=365)).strftime("%Y%m%d")
        df_ohlcv_year = stock.get_market_ohlcv_by_date(start_date, today_str, ticker)
        
        if not df_ohlcv_year.empty:
            summary["52주최고"] = df_ohlcv_year['고가'].max()
            summary["52주최저"] = df_ohlcv_year['저가'].min()
        else:
            summary["52주최고"] = "N/A"
            summary["52주최저"] = "N/A"
    except Exception as e:
        print(f"Error fetching 52-week high/low: {e}")
        summary["52주최고"] = "Error"
        summary["52주최저"] = "Error"
        
    return summary


# ----------------------------------------
# 4. GCS 업로드
# ----------------------------------------
def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """GCS 버킷에 파일을 업로드합니다."""
    if storage is None:
        print("❌ google-cloud-storage 라이브러리가 설치되지 않았습니다.")
        return

    try:
        # Cloud Functions에서는 인증 정보가 자동 처리됨 (ADC)
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        blob.upload_from_filename(source_file_name)

        print(f"✅ File {source_file_name} uploaded to {destination_blob_name}.")
    except Exception as e:
        print(f"❌ GCS 업로드 실패: {e}")

# ----------------------------------------
# 5. 메인 로직 (Cloud Functions 진입점)
# ----------------------------------------
# ----------------------------------------
# 5. 메인 로직 (Cloud Functions 진입점)
# ----------------------------------------
from bigquery_client import BigQueryClient

def main_process(ticker="005930"):
    print(f"\n▶ {ticker} 데이터 수집 및 분석 중...")

    # BigQuery 클라이언트 초기화
    bq = BigQueryClient()
    bq.create_dataset_if_not_exists()
    bq.create_table_if_not_exists()
    bq.update_schema_if_needed()

    # 1. 수집 기간 설정
    today = datetime.today()
    
    # BigQuery에서 마지막 적재일 확인
    last_date = bq.get_latest_date(ticker)
    
    if last_date:
        # 데이터가 있으면 마지막 날짜 다음날부터 수집
        start = datetime.combine(last_date, datetime.min.time()) + timedelta(days=1)
        print(f"🔄 기존 데이터 발견 (마지막 날짜: {last_date}). {start.date()} 부터 수집합니다.")
    else:
        # 데이터가 없으면 초기 30일 적재
        start = today - timedelta(days=30)
        print(f"🆕 신규 데이터. 최근 30일 데이터를 수집합니다.")

    # 미래 날짜인 경우 (이미 최신 데이터가 있는 경우)
    if start > today:
        print("✅ 이미 최신 데이터가 적재되어 있습니다.")
        return f"Already up to date: {ticker}"

    # 2. 상세 데이터 수집
    filename = f"{ticker}_data.csv"
    
    try:
        df_detail = fetch_one_ticker(ticker, start, today)
        
        if df_detail.empty:
            print("⚠️ 수집된 데이터가 없습니다 (휴장일 등).")
        else:
            df_detail = df_detail.sort_values("날짜", ascending=False)
            
            # CSV 저장 (옵션)
            df_detail.to_csv(filename, index=False, encoding="utf-8-sig")
            print(f"💾 상세 데이터 CSV 저장 완료: {filename}")
            
            # BigQuery 업로드
            bq.upload_dataframe(df_detail)
            
            # GCS 업로드 (기존 로직 유지)
            bucket_name = os.environ.get("BUCKET_NAME")
            if bucket_name:
                today_str = today.strftime("%Y%m%d")
                destination_blob_name = f"{today_str}/{filename}"
                upload_to_gcs(bucket_name, filename, destination_blob_name)
            
    except Exception as e:
        print(f"❌ 상세 데이터 수집/적재 중 오류 발생: {e}")
        # 오류 발생 시에도 요약 정보는 출력하도록 진행

    # 3. 요약 정보 수집 및 출력
    summary = get_ticker_summary(ticker)
    
    print("\n[ 요약 정보 ]")
    print(f"PER      : {summary.get('PER')}")
    print(f"PBR      : {summary.get('PBR')}")
    print(f"52주 최고: {summary.get('52주최고')}")
    print(f"52주 최저: {summary.get('52주최저')}")
    
    return f"Success: {ticker}"

# Cloud Functions (HTTP Trigger)
def cloud_function_entry(request):
    # 요청에서 티커 파라미터 확인 (기본값: 삼성전자)
    request_json = request.get_json(silent=True)
    request_args = request.args

    ticker = "005930"
    if request_json and 'ticker' in request_json:
        ticker = request_json['ticker']
    elif request_args and 'ticker' in request_args:
        ticker = request_args['ticker']
        
    return main_process(ticker)

# 로컬 실행용
if __name__ == "__main__":
    user_input = input("티커 코드를 입력하세요 (예: 005930, 엔터치면 기본값): ").strip()
    target_ticker = user_input if user_input else "005930"
    main_process(target_ticker)
