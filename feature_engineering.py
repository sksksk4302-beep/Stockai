import pandas as pd
import numpy as np

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    기본적인 기술적 지표(MA, RSI, Bollinger Bands, ATR 등)를 계산하여 DataFrame에 추가합니다.
    """
    df = df.copy()
    df = df.sort_values("date")  # 날짜 오름차순 정렬

    # 이동평균 (MA)
    for window in [5, 20, 60]:
        df[f'ma{window}'] = df['close'].rolling(window=window).mean()

    # RSI (14일)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi_change'] = df['rsi'].diff()

    # Bollinger Bands (20일, 2표준편차)
    ma20 = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['bb_upper'] = ma20 + (std20 * 2)
    df['bb_lower'] = ma20 - (std20 * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / ma20
    # BB Position: (Price - Lower) / (Upper - Lower)
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # ATR (14일)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    df['atr'] = true_range.rolling(window=14).mean()

    return df

def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    날짜 기반 피처 및 캔들 패턴 등 파생 피처를 추가합니다.
    """
    df = df.copy()
    
    # 날짜 관련
    df['date'] = pd.to_datetime(df['date'])
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['is_month_end'] = df['date'].dt.is_month_end
    # week_of_month: 대략적인 주차 계산
    df['week_of_month'] = df['date'].apply(lambda d: (d.day - 1) // 7 + 1)

    # 캔들 패턴
    # price_range: (high-low)/close
    df['price_range'] = (df['high'] - df['low']) / df['close']
    
    # body_ratio: |open-close|/close
    # 시가(open)가 없는 경우... pykrx ohlcv에는 시가가 있음.
    # main.py fetch_one_ticker에서 '시가'를 가져오는지 확인 필요. 
    # 현재 main.py는 '종가', '거래량'만 가져오고 있음. -> 수정 필요!
    # 일단 main.py 수정 전이라 가정하고, main.py도 수정해야 함.
    
    # 여기서는 main.py가 시가, 고가, 저가를 다 가져온다고 가정하고 작성.
    if 'open' in df.columns and 'high' in df.columns and 'low' in df.columns:
        df['body_ratio'] = np.abs(df['open'] - df['close']) / df['close']
        
        # Upper Shadow: (High - max(Open, Close)) / Close
        df['upper_shadow'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['close']
        
        # Lower Shadow: (min(Open, Close) - Low) / Close
        df['lower_shadow'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['close']

    # Volume Ratio (vs 20일 평균)
    df['volume_ratio'] = df['volume'] / df['volume'].rolling(window=20).mean()

    # 수급 비중 (거래대금 대비 순매수 비중)
    # 거래대금(trading_value)이 있다면 좋지만, 없다면 (종가 * 거래량)으로 추정
    est_trading_value = df['close'] * df['volume']
    # 0으로 나누기 방지
    est_trading_value = est_trading_value.replace(0, np.nan)
    
    if 'foreign_net_buy' in df.columns:
        df['foreign_participation'] = (df['foreign_net_buy'] * 10000) / est_trading_value # 단위 보정 필요할 수 있음 (main.py 확인)
        # main.py에서 inv = inv / 10000 했으므로, 다시 원복하려면 * 10000? 
        # 아니면 그냥 비율이니까... 
        # main.py: "1만 단위로 나누고 올림 처리" -> 즉 1 = 1만원.
        # 거래량 * 종가 = 원 단위.
        # 따라서 순매수 * 10000 / (거래량 * 종가)
        df['foreign_participation'] = (df['foreign_net_buy'] * 10000) / est_trading_value

    if 'institution_net_buy' in df.columns:
        df['institutional_participation'] = (df['institution_net_buy'] * 10000) / est_trading_value

    return df

def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    과거 데이터(Lag)를 추가합니다.
    """
    df = df.copy()
    
    # Close Lags
    for lag in [1, 2, 3, 5]:
        df[f'close_lag{lag}'] = df['close'].shift(lag)
        
    # Volume Lags
    for lag in [1, 2, 3]:
        df[f'volume_lag{lag}'] = df['volume'].shift(lag)
        
    # Return Lags (종가 등락률)
    # return_1d가 계산되어 있어야 함. (close_diff / close_lag1)
    # main.py에서 '종가전일비'는 diff()임. 수익률(%)이 아님.
    # 수익률 계산: df['close'].pct_change() * 100
    df['return_1d'] = df['close'].pct_change() * 100
    
    for lag in [1, 2, 3, 5]:
        df[f'return_lag{lag}'] = df['return_1d'].shift(lag)

    # Investor Lags
    if 'foreign_net_buy' in df.columns:
        df['foreign_net_lag1'] = df['foreign_net_buy'].shift(1)
    if 'institution_net_buy' in df.columns:
        df['institution_net_lag1'] = df['institution_net_buy'].shift(1)
        
    # Volatility Lags
    if 'atr' in df.columns:
        df['atr_lag1'] = df['atr'].shift(1)
    if 'bb_width' in df.columns:
        df['bb_width_lag1'] = df['bb_width'].shift(1)
        
    return df

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    이동평균 기반 통계량(Min, Max, Std 등)을 추가합니다.
    """
    df = df.copy()
    
    # 5일 통계
    df['close_5d_min'] = df['close'].rolling(window=5).min()
    df['close_5d_max'] = df['close'].rolling(window=5).max()
    df['close_5d_std'] = df['close'].rolling(window=5).std()
    
    df['volume_5d_mean'] = df['volume'].rolling(window=5).mean()
    df['volume_5d_std'] = df['volume'].rolling(window=5).std()
    
    if 'return_1d' not in df.columns:
        df['return_1d'] = df['close'].pct_change() * 100
        
    df['return_5d_mean'] = df['return_1d'].rolling(window=5).mean()
    df['return_5d_std'] = df['return_1d'].rolling(window=5).std()
    
    # 20일 통계
    df['close_20d_min'] = df['close'].rolling(window=20).min()
    df['close_20d_max'] = df['close'].rolling(window=20).max()
    
    # Sharpe Ratio (20일) - 무위험수익률 0 가정
    mean_return = df['return_1d'].rolling(window=20).mean()
    std_return = df['return_1d'].rolling(window=20).std()
    df['return_20d_sharpe'] = mean_return / std_return
    
    # Price Position vs MA
    for window in [5, 20, 60]:
        col = f'ma{window}'
        if col in df.columns:
            df[f'price_vs_{col}'] = (df['close'] - df[col]) / df[col]
            
    return df

def add_target_variables(df: pd.DataFrame) -> pd.DataFrame:
    """
    예측 대상(Target) 변수를 생성합니다. (미래 데이터 참조)
    """
    df = df.copy()
    
    # Next N-day returns
    # shift(-N)은 미래 데이터를 가져옴
    df['target_return_1d'] = df['close'].pct_change(periods=1).shift(-1) * 100
    df['target_return_3d'] = df['close'].pct_change(periods=3).shift(-3) * 100
    df['target_return_5d'] = df['close'].pct_change(periods=5).shift(-5) * 100
    
    df['target_close'] = df['close'].shift(-1)
    
    # Direction (1 if return > 0 else 0)
    df['target_direction'] = (df['target_return_1d'] > 0).astype(int)
    # NaN 처리는 나중에 (마지막 날은 target 알 수 없음)
    
    # Target High-Low Range (Next day)
    if 'high' in df.columns and 'low' in df.columns:
        next_high = df['high'].shift(-1)
        next_low = df['low'].shift(-1)
        next_close = df['close'].shift(-1)
        df['target_high_low_range'] = (next_high - next_low) / next_close

    return df

def process_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    전체 피처 엔지니어링 파이프라인을 실행합니다.
    """
    # 1. 기술적 지표
    df = add_technical_indicators(df)
    
    # 2. 파생 피처
    df = add_derived_features(df)
    
    # 3. Lag 피처
    df = add_lag_features(df)
    
    # 4. Rolling 통계
    df = add_rolling_features(df)
    
    # 5. Target 변수
    df = add_target_variables(df)
    
    return df
