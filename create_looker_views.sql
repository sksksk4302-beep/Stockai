-- ============================================
-- Looker Studio 차트용 BigQuery View 생성 스크립트
-- ============================================
-- 사용 전 반드시 프로젝트ID, 데이터셋ID를 실제 값으로 변경하세요!
-- 
-- 예시:
--   프로젝트ID: your-gcp-project
--   데이터셋ID: stock_data
--
-- 이 스크립트는 4개의 View를 생성합니다:
--   1. v_investor_volume  - 외국인/기관 순매수 vs 거래량
--   2. v_bollinger_price  - 볼린저밴드 + 종가
--   3. v_short_balance    - 공매도잔고
--   4. v_obv_rsi          - OBV + RSI
-- ============================================

-- ============================================
-- 차트 1: 외국인/기관 순매수 vs 거래량
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_investor_volume` AS
SELECT 
  date AS 날짜,
  ticker AS 종목코드,
  name AS 종목명,
  foreign_net_buy AS 외국인순매수,
  institution_net_buy AS 기관순매수,
  volume AS 거래량,
  -- 비율 계산 (참고용)
  SAFE_DIVIDE(foreign_net_buy * 10000, close * volume) AS 외국인순매수비율,
  SAFE_DIVIDE(institution_net_buy * 10000, close * volume) AS 기관순매수비율
FROM `tonal-land-477206-h3.stock_data.stock_daily`
WHERE volume > 0  -- 거래가 있는 날만
ORDER BY date DESC, ticker;

-- ============================================
-- 차트 2: 볼린저밴드 + 종가
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_bollinger_price` AS
SELECT 
  date AS 날짜,
  ticker AS 종목코드,
  name AS 종목명,
  close AS 종가,
  bb_upper AS 볼린저상단,
  bb_lower AS 볼린저하단,
  bb_position AS 볼린저위치,
  -- 이평선 추가 (참고용)
  ma20 AS 이평20일
FROM `tonal-land-477206-h3.stock_data.stock_daily`
WHERE bb_upper IS NOT NULL  -- 볼린저밴드 계산된 데이터만
ORDER BY date DESC, ticker;

-- ============================================
-- 차트 3: 공매도잔고
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_short_balance` AS
SELECT 
  date AS 날짜,
  ticker AS 종목코드,
  name AS 종목명,
  short_balance AS 공매도잔고,
  short_balance_diff AS 공매도잔고변화,
  -- 거래량 대비 공매도 비율 (참고용)
  SAFE_DIVIDE(short_balance, volume) AS 공매도비율
FROM `tonal-land-477206-h3.stock_data.stock_daily`
WHERE short_balance IS NOT NULL  -- 공매도 데이터가 있는 경우만
ORDER BY date DESC, ticker;

-- ============================================
-- 차트 4: OBV + RSI
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_obv_rsi` AS
SELECT 
  date AS 날짜,
  ticker AS 종목코드,
  name AS 종목명,
  obv AS OBV,
  rsi AS RSI,
  rsi_change AS RSI변화,
  -- 종가 추가 (비교용)
  close AS 종가
FROM `tonal-land-477206-h3.stock_data.stock_daily`
WHERE obv IS NOT NULL AND rsi IS NOT NULL  -- OBV, RSI 계산된 데이터만
ORDER BY date DESC, ticker;

-- ============================================
-- 실행 후 확인
-- ============================================
-- SELECT * FROM `tonal-land-477206-h3.stock_data.v_investor_volume` WHERE 종목코드 = '005930' LIMIT 10;
-- SELECT * FROM `tonal-land-477206-h3.stock_data.v_bollinger_price` WHERE 종목코드 = '005930' LIMIT 10;
-- SELECT * FROM `tonal-land-477206-h3.stock_data.v_short_balance` WHERE 종목코드 = '005930' LIMIT 10;
-- SELECT * FROM `tonal-land-477206-h3.stock_data.v_obv_rsi` WHERE 종목코드 = '005930' LIMIT 10;

-- ============================================
-- Looker Studio 사용 방법
-- ============================================
-- 1. 위 SQL에서 프로젝트ID, 데이터셋ID를 실제 값으로 변경
-- 2. BigQuery 콘솔에서 실행 (4개 View 생성)
-- 3. Looker Studio에서 각 View를 데이터 소스로 추가
--    - v_investor_volume  → 차트 1 생성
--    - v_bollinger_price  → 차트 2 생성
--    - v_short_balance    → 차트 3 생성
--    - v_obv_rsi          → 차트 4 생성
-- 4. 각 차트에서:
--    - X축: 날짜
--    - 필터: 종목코드 또는 종목명
--    - Y축: 해당 지표들
-- ============================================
