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
def fetch_one_ticker(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    특정 티커에 대해 다음 데이터를 수집:
      - OHLCV (시가, 고가, 저가, 종가, 거래량)
      - 투자자별 순매수 (개인, 외국인, 기관 세부)
      - 공매도 데이터
      - 펀더멘털 지표 (PER, PBR, EPS, BPS, 시가총액)
      - KOSPI 지수
      - 기술적 지표 (MA, RSI, MACD, Bollinger Bands, ATR 등)
    """
    import ta
    
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")

    # 1. OHLCV 데이터
    try:
        ohlcv = stock.get_market_ohlcv_by_date(start_str, end_str, ticker)
        ohlcv = ohlcv[["시가", "고가", "저가", "종가", "거래량"]].copy()
        ohlcv.columns = ["open", "high", "low", "close", "volume"]
        
        # 전일비 및 등락률 계산
        ohlcv["change"] = ohlcv["close"].diff()
        ohlcv["fluctuation_rate"] = (ohlcv["change"] / ohlcv["close"].shift(1) * 100).round(2)
        ohlcv["return_1d"] = ohlcv["fluctuation_rate"]  # 동일
        
        # 거래대금 계산 (종가 * 거래량)
        ohlcv["trading_value"] = ohlcv["close"] * ohlcv["volume"]
        
    except Exception as e:
        print(f"  └ Error fetching OHLCV for {ticker}: {e}")
        return pd.DataFrame()

    # 2. 투자자별 매매동향 (세부 분류)
    # pykrx 컬럼: 개인, 외국인, 기관합계, 금융투자, 보험, 투신, 사모, 은행, 기타금융, 연기금, 기타법인
    inv_mapping = {
        "개인": "individual_net",
        "외국인": "foreign_net",
        "기관합계": "institution_net",
        "연기금": "pension_net",
        "보험": "insurance_net",
        "투신": "trust_net",
        "기타금융": "etc_finance_net",
        "은행": "bank_net",
        "기타법인": "etc_corp_net"
    }
    
    try:
        inv = stock.get_market_trading_value_by_date(start_str, end_str, ticker)
        
        for kr_col, en_col in inv_mapping.items():
            if kr_col in inv.columns:
                ohlcv[en_col] = inv[kr_col]
            else:
                ohlcv[en_col] = pd.NA
                
    except Exception as e:
        print(f"  └ Warning: Could not fetch investor trading for {ticker}: {e}")
        for en_col in inv_mapping.values():
            ohlcv[en_col] = pd.NA

    # 3. 공매도 데이터
    try:
        short = stock.get_shorting_balance_by_date(start_str, end_str, ticker)
        ohlcv["short_volume"] = short["공매도잔고"] if "공매도잔고" in short.columns else pd.NA
        ohlcv["short_value"] = short["공매도금액"] if "공매도금액" in short.columns else pd.NA
        ohlcv["short_ratio"] = short["비중"] if "비중" in short.columns else pd.NA
        
        # 대차잔고 (주식 대여)
        # Note: 실제로는 별도 API 필요, 일단 공매도 데이터로 대체
        ohlcv["loan_balance"] = ohlcv["short_volume"]
        ohlcv["loan_balance_change"] = ohlcv["loan_balance"].diff()
        ohlcv["loan_balance_value"] = ohlcv["short_value"]
        
    except Exception as e:
        print(f"  └ Warning: Could not fetch short selling data for {ticker}: {e}")
        ohlcv["short_volume"] = pd.NA
        ohlcv["short_value"] = pd.NA
        ohlcv["short_ratio"] = pd.NA
        ohlcv["loan_balance"] = pd.NA
        ohlcv["loan_balance_change"] = pd.NA
        ohlcv["loan_balance_value"] = pd.NA

    # 4. 펀더멘털 & 시가총액
    try:
        fund = stock.get_market_fundamental_by_date(start_str, end_str, ticker)
        ohlcv["per"] = fund["PER"] if "PER" in fund.columns else pd.NA
        ohlcv["eps"] = fund["EPS"] if "EPS" in fund.columns else pd.NA
        ohlcv["pbr"] = fund["PBR"] if "PBR" in fund.columns else pd.NA
        ohlcv["bps"] = fund["BPS"] if "BPS" in fund.columns else pd.NA
        
        # 시가총액 = 종가 * 상장주식수 (상장주식수는 별도 조회 필요)
        try:
            cap = stock.get_market_cap_by_date(start_str, end_str, ticker)
            ohlcv["market_cap"] = cap["시가총액"] if "시가총액" in cap.columns else pd.NA
            ohlcv["shares_outstanding"] = cap["상장주식수"] if "상장주식수" in cap.columns else pd.NA
        except:
            ohlcv["market_cap"] = pd.NA
            ohlcv["shares_outstanding"] = pd.NA
            
    except Exception as e:
        print(f"  └ Warning: Could not fetch fundamental data for {ticker}: {e}")
        ohlcv["per"] = pd.NA
        ohlcv["eps"] = pd.NA
        ohlcv["pbr"] = pd.NA
        ohlcv["bps"] = pd.NA
        ohlcv["market_cap"] = pd.NA
        ohlcv["shares_outstanding"] = pd.NA

    # 5. KOSPI 지수 데이터
    try:
        kospi = stock.get_index_ohlcv_by_date(start_str, end_str, "1001")  # KOSPI 코드
        ohlcv["kospi_open"] = kospi["시가"]
        ohlcv["kospi_high"] = kospi["고가"]
        ohlcv["kospi_low"] = kospi["저가"]
        ohlcv["kospi_close"] = kospi["종가"]
        ohlcv["kospi_volume"] = kospi["거래량"]
    except Exception as e:
        print(f"  └ Warning: Could not fetch KOSPI index: {e}")
        ohlcv["kospi_open"] = pd.NA
        ohlcv["kospi_high"] = pd.NA
        ohlcv["kospi_low"] = pd.NA
        ohlcv["kospi_close"] = pd.NA
        ohlcv["kospi_volume"] = pd.NA

    # 6. 환율 (KRW/USD) - pykrx에 없으므로 일단 NULL
    ohlcv["krw_usd"] = pd.NA

    # 7. 기술적 지표 계산 (ta library 사용)
    try:
        # 이동평균
        ohlcv["ma5"] = ta.trend.sma_indicator(ohlcv["close"], window=5)
        ohlcv["ma20"] = ta.trend.sma_indicator(ohlcv["close"], window=20)
        ohlcv["ma60"] = ta.trend.sma_indicator(ohlcv["close"], window=60)
        ohlcv["ma120"] = ta.trend.sma_indicator(ohlcv["close"], window=120)
        
        # 거래량 이동평균
        ohlcv["volume_ma5"] = ta.trend.sma_indicator(ohlcv["volume"], window=5)
        ohlcv["volume_ma20"] = ta.trend.sma_indicator(ohlcv["volume"], window=20)
        
        # 정규화 거래량
        ohlcv["vol_norm"] = ohlcv["volume"] / ohlcv["volume_ma20"]
        
        # RSI
        ohlcv["rsi_14"] = ta.momentum.rsi(ohlcv["close"], window=14)
        
        # MACD
        macd = ta.trend.MACD(ohlcv["close"], window_fast=12, window_slow=26, window_sign=9)
        ohlcv["macd"] = macd.macd()
        ohlcv["macd_signal"] = macd.macd_signal()
        ohlcv["macd_hist"] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(ohlcv["close"], window=20, window_dev=2)
        ohlcv["bb_upper"] = bb.bollinger_hband()
        ohlcv["bb_middle"] = bb.bollinger_mavg()
        ohlcv["bb_lower"] = bb.bollinger_lband()
        ohlcv["bb_width"] = bb.bollinger_wband()
        
        # ATR
        ohlcv["atr_14"] = ta.volatility.average_true_range(
            ohlcv["high"], ohlcv["low"], ohlcv["close"], window=14
        )
        
        # ROC
        ohlcv["roc_10"] = ta.momentum.roc(ohlcv["close"], window=10)
        
        # Momentum (간단 계산: close - close.shift(10))
        ohlcv["momentum_10"] = ohlcv["close"] - ohlcv["close"].shift(10)
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(
            ohlcv["high"], ohlcv["low"], ohlcv["close"], 
            window=14, smooth_window=3
        )
        ohlcv["stoch_k"] = stoch.stoch()
        ohlcv["stoch_d"] = stoch.stoch_signal()
            
    except Exception as e:
        print(f"  └ Warning: Error calculating technical indicators for {ticker}: {e}")

    # 8. 메타데이터 추가
    ohlcv["ticker"] = ticker
    ohlcv["name"] = stock.get_market_ticker_name(ticker)
    
    # index(날짜)를 컬럼으로
    ohlcv = ohlcv.reset_index()
    if "index" in ohlcv.columns:
        ohlcv = ohlcv.rename(columns={"index": "date"})
    elif "날짜" in ohlcv.columns:
        ohlcv = ohlcv.rename(columns={"날짜": "date"})
    
    return ohlcv



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
    bq = get_bq_client()
    
    # 요청 파싱
    request_json = request.get_json(silent=True)
    request_args = request.args
    
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
