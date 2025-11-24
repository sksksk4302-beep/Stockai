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

    # 6. 환율 (KRW/USD) - pykrx에 없으므로 일단 NULL
    ohlcv["krw_usd"] = pd.NA

    # 7. 기술적 지표 계산 (ta library 사용)
    # 이동평균
    try:
        ohlcv["ma5"] = ta.trend.sma_indicator(ohlcv["close"], window=5)
        ohlcv["ma20"] = ta.trend.sma_indicator(ohlcv["close"], window=20)
        ohlcv["ma60"] = ta.trend.sma_indicator(ohlcv["close"], window=60)
        ohlcv["ma120"] = ta.trend.sma_indicator(ohlcv["close"], window=120)
    except Exception as e:
        print(f"  └ Warning: MA calculation error: {e}")
        ohlcv["ma5"] = pd.NA
        ohlcv["ma20"] = pd.NA
        ohlcv["ma60"] = pd.NA
        ohlcv["ma120"] = pd.NA
    
    # 거래량 이동평균
    try:
        ohlcv["volume_ma5"] = ta.trend.sma_indicator(ohlcv["volume"], window=5)
        ohlcv["volume_ma20"] = ta.trend.sma_indicator(ohlcv["volume"], window=20)
    except Exception as e:
        print(f"  └ Warning: Volume MA calculation error: {e}")
        ohlcv["volume_ma5"] = pd.NA
        ohlcv["volume_ma20"] = pd.NA
    
    # 정규화 거래량
    try:
        ohlcv["vol_norm"] = ohlcv["volume"] / ohlcv["volume_ma20"]
    except:
        ohlcv["vol_norm"] = pd.NA
    
    # RSI
    try:
        ohlcv["rsi_14"] = ta.momentum.rsi(ohlcv["close"], window=14)
    except Exception as e:
        print(f"  └ Warning: RSI calculation error: {e}")
        ohlcv["rsi_14"] = pd.NA
    
    # MACD
    try:
        macd = ta.trend.MACD(ohlcv["close"], window_fast=12, window_slow=26, window_sign=9)
        ohlcv["macd"] = macd.macd()
        ohlcv["macd_signal"] = macd.macd_signal()
        ohlcv["macd_hist"] = macd.macd_diff()
    except Exception as e:
        print(f"  └ Warning: MACD calculation error: {e}")
        ohlcv["macd"] = pd.NA
        ohlcv["macd_signal"] = pd.NA
        ohlcv["macd_hist"] = pd.NA
    
    # Bollinger Bands
    try:
        bb = ta.volatility.BollingerBands(ohlcv["close"], window=20, window_dev=2)
        ohlcv["bb_upper"] = bb.bollinger_hband()
        ohlcv["bb_middle"] = bb.bollinger_mavg()
        ohlcv["bb_lower"] = bb.bollinger_lband()
        ohlcv["bb_width"] = bb.bollinger_wband()
    except Exception as e:
        print(f"  └ Warning: Bollinger Bands calculation error: {e}")
        ohlcv["bb_upper"] = pd.NA
        ohlcv["bb_middle"] = pd.NA
        ohlcv["bb_lower"] = pd.NA
        ohlcv["bb_width"] = pd.NA
    
    # ATR
    try:
        ohlcv["atr_14"] = ta.volatility.average_true_range(
            ohlcv["high"], ohlcv["low"], ohlcv["close"], window=14
        )
    except Exception as e:
        print(f"  └ Warning: ATR calculation error: {e}")
        ohlcv["atr_14"] = pd.NA
    
    # ROC
    try:
        ohlcv["roc_10"] = ta.momentum.roc(ohlcv["close"], window=10)
    except Exception as e:
        print(f"  └ Warning: ROC calculation error: {e}")
        ohlcv["roc_10"] = pd.NA
    
    # Momentum
    try:
        ohlcv["momentum_10"] = ohlcv["close"] - ohlcv["close"].shift(10)
    except:
        ohlcv["momentum_10"] = pd.NA
    
    # Stochastic
    try:
        stoch = ta.momentum.StochasticOscillator(
            ohlcv["high"], ohlcv["low"], ohlcv["close"], 
            window=14, smooth_window=3
        )
        ohlcv["stoch_k"] = stoch.stoch()
        ohlcv["stoch_d"] = stoch.stoch_signal()
    except Exception as e:
        print(f"  └ Warning: Stochastic calculation error: {e}")
        ohlcv["stoch_k"] = pd.NA
        ohlcv["stoch_d"] = pd.NA

    # 8. 메타데이터 추가
    ohlcv["ticker"] = ticker
    ohlcv["name"] = stock.get_market_ticker_name(ticker)
    
    # index(날짜)를 컬럼으로
<<<<<<< HEAD
    ohlcv = ohlcv.reset_index()
    if "index" in ohlcv.columns:
        ohlcv = ohlcv.rename(columns={"index": "date"})
    elif "날짜" in ohlcv.columns:
        ohlcv = ohlcv.rename(columns={"날짜": "date"})
    
    # 9. 파생 피처 계산
    try:
        # 시간 관련 피처
        ohlcv["day_of_week"] = pd.to_datetime(ohlcv["date"]).dt.dayofweek  # 0=Monday
        ohlcv["week_of_month"] = (pd.to_datetime(ohlcv["date"]).dt.day - 1) // 7 + 1
        ohlcv["month"] = pd.to_datetime(ohlcv["date"]).dt.month
        
        # 월말 여부 (해당 월의 마지막 거래일)
        ohlcv["is_month_end"] = False
        if len(ohlcv) > 0:
            for i in range(len(ohlcv) - 1):
                curr_month = pd.to_datetime(ohlcv.iloc[i]["date"]).month
                next_month = pd.to_datetime(ohlcv.iloc[i+1]["date"]).month
                if curr_month != next_month:
                    ohlcv.at[i, "is_month_end"] = True
            # 마지막 행도 체크
            if i == len(ohlcv) - 2:
                ohlcv.at[len(ohlcv)-1, "is_month_end"] = True
    except Exception as e:
        print(f"  └ Warning: Time features calculation error: {e}")
        ohlcv["day_of_week"] = pd.NA
        ohlcv["week_of_month"] = pd.NA
        ohlcv["month"] = pd.NA
        ohlcv["is_month_end"] = False
    
    try:
        # KOSPI 대비 수익률
        kospi_return = ohlcv["kospi_close"].pct_change() * 100
        ohlcv["return_vs_kospi"] = ohlcv["return_1d"] - kospi_return
    except:
        ohlcv["return_vs_kospi"] = pd.NA
    
    try:
        # 가격 범위 (변동폭)
        ohlcv["price_range"] = (ohlcv["high"] - ohlcv["low"]) / ohlcv["close"]
        
        # 캔들 패턴 분석
        body_top = ohlcv[["open", "close"]].max(axis=1)
        body_bottom = ohlcv[["open", "close"]].min(axis=1)
        
        ohlcv["upper_shadow"] = (ohlcv["high"] - body_top) / ohlcv["close"]
        ohlcv["lower_shadow"] = (body_bottom - ohlcv["low"]) / ohlcv["close"]
        ohlcv["body_ratio"] = abs(ohlcv["open"] - ohlcv["close"]) / ohlcv["close"]
    except Exception as e:
        print(f"  └ Warning: Price pattern calculation error: {e}")
        ohlcv["price_range"] = pd.NA
        ohlcv["upper_shadow"] = pd.NA
        ohlcv["lower_shadow"] = pd.NA
        ohlcv["body_ratio"] = pd.NA
    
    try:
        # 거래량 비율 (vol_norm과 동일)
        ohlcv["volume_ratio"] = ohlcv["vol_norm"]
    except:
        ohlcv["volume_ratio"] = pd.NA
    
    try:
        # 투자자 참여도 (순매수 / 거래대금)
        ohlcv["foreign_participation"] = (ohlcv["foreign_net"] / ohlcv["trading_value"] * 100).replace([np.inf, -np.inf], pd.NA)
        ohlcv["institutional_participation"] = (ohlcv["institution_net"] / ohlcv["trading_value"] * 100).replace([np.inf, -np.inf], pd.NA)
    except Exception as e:
        print(f"  └ Warning: Participation calculation error: {e}")
        ohlcv["foreign_participation"] = pd.NA
        ohlcv["institutional_participation"] = pd.NA
    
    # 10. ML 피처 계산 (Target, Lag, Rolling Stats)
    # 데이터 정렬 확인 (시간 순서 중요!)
    ohlcv = ohlcv.sort_index()
    
    # === Target 변수 (예측 목표) ===
    try:
        # 다음날 수익률 계산
        ohlcv["target_return_1d"] = ohlcv["close"].pct_change(1).shift(-1) * 100
        
        # 3일, 5일 후 수익률
        ohlcv["target_return_3d"] = ohlcv["close"].pct_change(3).shift(-3) * 100
        ohlcv["target_return_5d"] = ohlcv["close"].pct_change(5).shift(-5) * 100
        
        # 다음날 종가
        ohlcv["target_close"] = ohlcv["close"].shift(-1)
        
        # 상승/하락 방향 (1=상승, 0=하락)
        ohlcv["target_direction"] = (ohlcv["target_return_1d"] > 0).astype(int)
        
        # 다음날 변동폭
        ohlcv["target_high_low_range"] = ((ohlcv["high"] - ohlcv["low"]) / ohlcv["close"]).shift(-1)
    except Exception as e:
        print(f"  └ Warning: Target variables calculation error: {e}")
        for col in ["target_return_1d", "target_return_3d", "target_return_5d", 
                    "target_close", "target_direction", "target_high_low_range"]:
            ohlcv[col] = pd.NA
    
    # === Lag Features (과거 값) ===
    try:
        # 종가 Lag
        ohlcv["close_lag1"] = ohlcv["close"].shift(1)
        ohlcv["close_lag2"] = ohlcv["close"].shift(2)
        ohlcv["close_lag3"] = ohlcv["close"].shift(3)
        ohlcv["close_lag5"] = ohlcv["close"].shift(5)
        
        # 거래량 Lag
        ohlcv["volume_lag1"] = ohlcv["volume"].shift(1)
        ohlcv["volume_lag2"] = ohlcv["volume"].shift(2)
        ohlcv["volume_lag3"] = ohlcv["volume"].shift(3)
        
        # 수익률 Lag
        ohlcv["return_lag1"] = ohlcv["return_1d"].shift(1)
        ohlcv["return_lag2"] = ohlcv["return_1d"].shift(2)
        ohlcv["return_lag3"] = ohlcv["return_1d"].shift(3)
        ohlcv["return_lag5"] = ohlcv["return_1d"].shift(5)
        
        # 투자자 Lag
        ohlcv["foreign_net_lag1"] = ohlcv["foreign_net"].shift(1)
        ohlcv["institution_net_lag1"] = ohlcv["institution_net"].shift(1)
        
        # 변동성 Lag
        ohlcv["atr_lag1"] = ohlcv["atr_14"].shift(1)
        ohlcv["bb_width_lag1"] = ohlcv["bb_width"].shift(1)
    except Exception as e:
        print(f"  └ Warning: Lag features calculation error: {e}")
        lag_cols = ["close_lag1", "close_lag2", "close_lag3", "close_lag5",
                    "volume_lag1", "volume_lag2", "volume_lag3",
                    "return_lag1", "return_lag2", "return_lag3", "return_lag5",
                    "foreign_net_lag1", "institution_net_lag1",
                    "atr_lag1", "bb_width_lag1"]
        for col in lag_cols:
            ohlcv[col] = pd.NA
    
    # === Rolling Statistics (과거 N일 통계) ===
    try:
        # 최근 5일 통계
        ohlcv["close_5d_min"] = ohlcv["close"].rolling(5).min()
        ohlcv["close_5d_max"] = ohlcv["close"].rolling(5).max()
        ohlcv["close_5d_std"] = ohlcv["close"].rolling(5).std()
        ohlcv["volume_5d_mean"] = ohlcv["volume"].rolling(5).mean()
        ohlcv["volume_5d_std"] = ohlcv["volume"].rolling(5).std()
        ohlcv["return_5d_mean"] = ohlcv["return_1d"].rolling(5).mean()
        ohlcv["return_5d_std"] = ohlcv["return_1d"].rolling(5).std()
        
        # 최근 20일 통계
        ohlcv["close_20d_min"] = ohlcv["close"].rolling(20).min()
        ohlcv["close_20d_max"] = ohlcv["close"].rolling(20).max()
        
        # 샤프 비율 (20일)
        mean_return = ohlcv["return_1d"].rolling(20).mean()
        std_return = ohlcv["return_1d"].rolling(20).std()
        ohlcv["return_20d_sharpe"] = (mean_return / std_return).replace([np.inf, -np.inf], pd.NA)
    except Exception as e:
        print(f"  └ Warning: Rolling statistics calculation error: {e}")
        rolling_cols = ["close_5d_min", "close_5d_max", "close_5d_std",
                        "volume_5d_mean", "volume_5d_std",
                        "return_5d_mean", "return_5d_std",
                        "close_20d_min", "close_20d_max", "return_20d_sharpe"]
        for col in rolling_cols:
            ohlcv[col] = pd.NA
    
    # === Price Position (가격 위치) ===
    try:
        # MA 대비 위치
        ohlcv["price_vs_ma5"] = ((ohlcv["close"] - ohlcv["ma5"]) / ohlcv["ma5"] * 100).replace([np.inf, -np.inf], pd.NA)
        ohlcv["price_vs_ma20"] = ((ohlcv["close"] - ohlcv["ma20"]) / ohlcv["ma20"] * 100).replace([np.inf, -np.inf], pd.NA)
        ohlcv["price_vs_ma60"] = ((ohlcv["close"] - ohlcv["ma60"]) / ohlcv["ma60"] * 100).replace([np.inf, -np.inf], pd.NA)
        
        # Bollinger Band 내 위치 (0~1)
        bb_range = ohlcv["bb_upper"] - ohlcv["bb_lower"]
        ohlcv["bb_position"] = ((ohlcv["close"] - ohlcv["bb_lower"]) / bb_range).replace([np.inf, -np.inf], pd.NA)
        
        # RSI 변화
        ohlcv["rsi_change"] = ohlcv["rsi_14"].diff()
    except Exception as e:
        print(f"  └ Warning: Price position calculation error: {e}")
        for col in ["price_vs_ma5", "price_vs_ma20", "price_vs_ma60", "bb_position", "rsi_change"]:
            ohlcv[col] = pd.NA
    
    return ohlcv
=======
    df = df.reset_index().rename(columns={"index": "date"})
    
    # ----- 2-6. Feature Engineering -----
    # 피처 계산 적용
    df = process_features(df)
    
    return df
>>>>>>> 5ba74ae (Feat: Implement ML feature engineering and update BigQuery schema)



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
