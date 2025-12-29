-- ============================================
-- BigQuery Korean View 생성 스크립트
-- ============================================
-- 사용 전 반드시 프로젝트ID, 데이터셋ID, 테이블명을 실제 값으로 변경하세요!
-- 
-- 예시:
--   프로젝트ID: your-gcp-project그림
--   데이터셋ID: stock_data
--   테이블명: stock_daily
--
-- 실행 후 Looker Studio에서 'stock_daily_kr' View를 연결하면
-- 모든 필드가 한글로 표시됩니다!
-- ============================================

CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.stock_daily_kr` AS
SELECT 
  -- 기본 정보
  date AS `날짜`,
  ticker AS `종목코드`,
  name AS `종목명`,
  
  -- 가격 정보 (OHLCV)
  open AS `시가`,
  high AS `고가`,
  low AS `저가`,
  close AS `종가`,
  volume AS `거래량`,
  close_diff AS `전일대비`,
  volume_diff AS `거래량차이`,
  
  -- 투자자별 순매수 (단위: 만원)
  individual_net_buy AS `개인순매수`,
  foreign_net_buy AS `외국인순매수`,
  institution_net_buy AS `기관순매수`,
  
  -- 공매도
  short_balance AS `공매도잔고`,
  short_balance_diff AS `공매도잔고변화`,
  
  -- 재무지표
  bps AS `주당순자산`,
  per AS `PER`,
  pbr AS `PBR`,
  eps AS `주당순이익`,
  estimated_eps AS `예상EPS`,
  
  -- 이동평균 (MA)
  ma5 AS `이평5일`,
  ma20 AS `이평20일`,
  ma60 AS `이평60일`,
  ma120 AS `이평120일`,
  
  -- 기술적 지표
  rsi AS `RSI`,
  rsi_change AS `RSI변화`,
  bb_upper AS `볼린저상단`,
  bb_lower AS `볼린저하단`,
  bb_width AS `볼린저폭`,
  bb_position AS `볼린저위치`,
  atr AS `ATR`,
  obv AS `OBV`,
  
  -- 시간 정보
  day_of_week AS `요일`,
  month AS `월`,
  is_month_end AS `월말여부`,
  week_of_month AS `주차`,
  
  -- 캔들 패턴
  price_range AS `일일변동폭`,
  body_ratio AS `캔들몸통비`,
  upper_shadow AS `윗꼬리`,
  lower_shadow AS `아랫꼬리`,
  
  -- 거래량 및 참여도
  volume_ratio AS `거래량비율`,
  foreign_participation AS `외국인참여도`,
  institutional_participation AS `기관참여도`,
  
  -- 과거 데이터 (Lag)
  close_lag1 AS `종가_1일전`,
  close_lag2 AS `종가_2일전`,
  close_lag3 AS `종가_3일전`,
  close_lag5 AS `종가_5일전`,
  volume_lag1 AS `거래량_1일전`,
  volume_lag2 AS `거래량_2일전`,
  volume_lag3 AS `거래량_3일전`,
  
  -- 수익률
  return_1d AS `수익률_1일`,
  return_lag1 AS `수익률_1일전`,
  return_lag2 AS `수익률_2일전`,
  return_lag3 AS `수익률_3일전`,
  return_lag5 AS `수익률_5일전`,
  
  -- 투자자별 과거 데이터
  foreign_net_lag1 AS `외국인순매수_1일전`,
  institution_net_lag1 AS `기관순매수_1일전`,
  
  -- 기술지표 과거 데이터
  atr_lag1 AS `ATR_1일전`,
  bb_width_lag1 AS `볼린저폭_1일전`,
  
  -- 5일 통계
  close_5d_min AS `종가_5일최저`,
  close_5d_max AS `종가_5일최고`,
  close_5d_std AS `종가_5일표준편차`,
  volume_5d_mean AS `거래량_5일평균`,
  volume_5d_std AS `거래량_5일표준편차`,
  return_5d_mean AS `수익률_5일평균`,
  return_5d_std AS `수익률_5일표준편차`,
  
  -- 20일 통계
  close_20d_min AS `종가_20일최저`,
  close_20d_max AS `종가_20일최고`,
  return_20d_sharpe AS `샤프비율_20일`,
  
  -- 이동평균 대비 가격
  price_vs_ma5 AS `이평5일괴리율`,
  price_vs_ma20 AS `이평20일괴리율`,
  price_vs_ma60 AS `이평60일괴리율`,
  price_vs_ma120 AS `이평120일괴리율`,
  
  -- 예측 타겟 (예측 모델용)
  target_return_1d AS `목표수익률_1일`,
  target_return_3d AS `목표수익률_3일`,
  target_return_5d AS `목표수익률_5일`,
  target_close AS `다음날종가`,
  target_direction AS `상승하락`,
  target_high_low_range AS `다음날변동폭`

FROM `tonal-land-477206-h3.stock_data.daily_metrics`

-- ============================================
-- 사용 예시:
-- ============================================
-- 1. 위 SQL에서 프로젝트ID, 데이터셋ID를 실제 값으로 변경
-- 2. BigQuery 콘솔에서 실행
-- 3. Looker Studio에서 데이터 소스 추가 → BigQuery → stock_daily_kr 선택
-- 4. 완료! 모든 필드가 한글로 표시됩니다.
-- ============================================
