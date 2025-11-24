from pykrx import stock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json

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
from feature_engineering import process_features

def fetch_one_ticker(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    특정 티커에 대해:
      - OHLCV (Open, High, Low, Close, Volume)
      - 투자자별 매매동향
      - 공매도/대차잔고
      - 펀더멘털 지표
      - **ML 피처 엔지니어링 적용**
    를 모두 합쳐서 DataFrame으로 반환
    """
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    # ----- 2-1. 가격/거래량 (OHLCV) -----
    # 시가, 고가, 저가, 종가, 거래량 모두 가져옴
    price = stock.get_market_ohlcv_by_date(start_str, end_str, ticker)
    
    # 컬럼 영문 변환
    price = price[["시가", "고가", "저가", "종가", "거래량"]].copy()
    price.columns = ["open", "high", "low", "close", "volume"]
    
    # 전일비 계산 (기존 로직 유지)
    price["close_diff"] = price["close"].diff()
    price["volume_diff"] = price["volume"].diff()

    # ----- 2-2. 투자자별 매매동향 (순매수 거래대금 기준) -----
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

    inv.columns = ["individual_net_buy", "foreign_net_buy", "institution_net_buy"]

    # ----- 2-3. 공매도 잔고 (대차잔고 유사) -----
    try:
        short_bal = stock.get_shorting_balance_by_date(start_str, end_str, ticker)
        short_bal = short_bal[["공매도잔고"]].copy()
        short_bal.columns = ["short_balance"]
        short_bal["short_balance_diff"] = short_bal["short_balance"].diff()
    except Exception:
        short_bal = pd.DataFrame(index=price.index)
        short_bal["short_balance"] = pd.NA
        short_bal["short_balance_diff"] = pd.NA

    # ----- 2-4. 펀더멘털 지표 -----
    try:
        fundamental = stock.get_market_fundamental_by_date(start_str, end_str, ticker)
        fundamental = fundamental[["BPS", "PER", "PBR", "EPS"]].copy()
        fundamental.columns = ["bps", "per", "pbr", "eps"]
        fundamental["estimated_eps"] = pd.NA
    except Exception as e:
        print(f"Warning: Could not fetch fundamental data for {ticker}: {e}")
        fundamental = pd.DataFrame(index=price.index)
        for col in ["bps", "per", "pbr", "eps", "estimated_eps"]:
            fundamental[col] = pd.NA

    # ----- 2-5. 데이터 병합 -----
    df = price.join(inv, how="left").join(short_bal, how="left").join(fundamental, how="left")

    df["ticker"] = ticker
    df["name"] = stock.get_market_ticker_name(ticker)

    df = df.reset_index().rename(columns={"index": "date"})
    
    # ----- 2-6. Feature Engineering -----
    # 피처 계산 적용
    df = process_features(df)
    
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
# 4. 티커 목록 로드
# ----------------------------------------
def load_tickers():
    try:
        with open('tickers.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading tickers.json: {e}")
        return []

# ----------------------------------------
# 5. 메인 로직 (Cloud Functions 진입점)
# ----------------------------------------
# ----------------------------------------
# 5. 메인 로직 (Cloud Functions 진입점)
# ----------------------------------------
from bigquery_client import BigQueryClient

# 전역 클라이언트 (콜드 스타트 시에만 초기화)
bq_client = None

def get_bq_client():
    global bq_client
    if bq_client is None:
        bq_client = BigQueryClient()
        bq_client.create_dataset_if_not_exists()
        bq_client.create_table_if_not_exists()
        bq_client.update_schema_if_needed()
    return bq_client

def process_ticker_data(ticker, bq):
    """
    개별 티커의 데이터를 수집하여 DataFrame을 반환합니다.
    업로드는 하지 않습니다.
    """
    print(f"\n▶ {ticker} 데이터 수집 중...")

    # 1. 수집 기간 설정
    today = datetime.today()
    
    # BigQuery에서 마지막 적재일 확인
    last_date = bq.get_latest_date(ticker)
    
    if last_date:
        start = datetime.combine(last_date, datetime.min.time()) + timedelta(days=1)
        print(f"  └ 🔄 기존 데이터 발견 (Last: {last_date}). {start.date()} 부터 수집.")
    else:
        start = today - timedelta(days=30)
        print(f"  └ 🆕 신규 데이터. 최근 30일 수집.")

    # 미래 날짜인 경우
    if start.date() > today.date():
        print("  └ ✅ 이미 최신입니다.")
        return None

    # 2. 상세 데이터 수집
    try:
        df_detail = fetch_one_ticker(ticker, start, today)
        
        # 휴장일(거래량 0) 및 데이터 없는 날 제거
        if not df_detail.empty:
            df_detail = df_detail[df_detail['volume'] > 0]
        
        if df_detail.empty:
            print("  └ ⚠️ 수집된 데이터가 없습니다 (휴장일 등).")
            return None
            
        return df_detail
            
    except Exception as e:
        print(f"  └ ❌ 수집 중 오류 발생: {e}")
        return None

def main_process(ticker="005930"):
    """
    단일 티커 처리 (기존 호환성 유지 및 테스트용)
    """
    bq = get_bq_client()
    df = process_ticker_data(ticker, bq)
    
    if df is not None:
        bq.upload_dataframe(df)
        print(f"✅ {ticker} 업로드 완료 ({len(df)} rows)")
        
        # GCS 업로드 (옵션)
        bucket_name = os.environ.get("BUCKET_NAME")
        if bucket_name:
            filename = f"{ticker}_data.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            today_str = datetime.today().strftime("%Y%m%d")
            upload_to_gcs(bucket_name, filename, f"{today_str}/{filename}")

    # 요약 정보 출력
    summary = get_ticker_summary(ticker)
    print(f"[ {ticker} 요약 ] PER: {summary.get('PER')}, PBR: {summary.get('PBR')}")
    
    return f"Success: {ticker}"

# Cloud Functions (HTTP Trigger)
def cloud_function_entry(request):
    try:
        # Health check endpoint - only for specific health check requests
        if request.path == '/health' or (request.args and request.args.get('health') == 'check'):
            return {
                'status': 'ok',
                'service': 'stockaibot',
                'message': 'Service is running. Call without params to process all tickers, or use ?ticker=005930 for specific ticker.'
            }
        
        bq = get_bq_client()
        
        # 요청 파싱
        request_json = request.get_json(silent=True)
        request_args = request.args
        
        # 특수 액션 체크 (테이블 재생성)
        action = None
        if request_json and 'action' in request_json:
            action = request_json['action']
        elif request_args and 'action' in request_args:
            action = request_args['action']
        
        if action == 'recreate_table':
            try:
                # 기존 테이블 삭제
                bq.client.delete_table(bq.table_id)
                print(f"✅ 기존 테이블 삭제 완료: {bq.table_id}")
            except Exception as e:
                print(f"⚠️ 테이블 삭제 중 오류 (무시 가능): {e}")
            
            # 새 테이블 생성
            bq.create_dataset_if_not_exists()
            bq.create_table_if_not_exists()
            
            return f"✅ 테이블 재생성 완료: {bq.table_id}"
        
        ticker = None
        if request_json and 'ticker' in request_json:
            ticker = request_json['ticker']
        elif request_args and 'ticker' in request_args:
            ticker = request_args['ticker']
            
        # 1. 단일 티커 처리
        if ticker:
            return main_process(ticker)
        
        # 2. 전체 티커 일괄 처리 (Batch Processing)
        else:
            tickers = load_tickers()
            print(f"🚀 전체 {len(tickers)}개 종목 일괄 처리를 시작합니다.")
            
            all_dataframes = []
            results = []
            
            for t in tickers:
                code = t['code']
                name = t['name']
                
                try:
                    df = process_ticker_data(code, bq)
                    if df is not None:
                        all_dataframes.append(df)
                        results.append(f"{name}: Collected {len(df)} rows")
                    else:
                        results.append(f"{name}: Up to date or No data")
                except Exception as e:
                    print(f"Error processing {name}: {e}")
                    results.append(f"{name}: Error")
            
            # 일괄 업로드
            if all_dataframes:
                print(f"\n💾 총 {len(all_dataframes)}개 종목 데이터를 병합하여 BigQuery에 업로드합니다...")
                merged_df = pd.concat(all_dataframes, ignore_index=True)
                bq.upload_dataframe(merged_df)
                print("✨ 전체 업로드 완료!")
            else:
                print("\n✨ 업로드할 데이터가 없습니다.")
                
            return "\n".join(results)
    
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return {'error': str(e), 'traceback': traceback.format_exc()}, 500

if __name__ == "__main__":
    # 로컬 테스트
    user_input = input("티커 입력 (엔터=전체): ").strip()
    if user_input:
        main_process(user_input)
    else:
        # Mock Request
        class MockRequest:
            def get_json(self, silent=True): return None
            @property
            def args(self): return {}
        cloud_function_entry(MockRequest())
