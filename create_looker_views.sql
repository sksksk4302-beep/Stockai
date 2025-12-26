-- ============================================
-- BigQuery Views for Looker Studio Charts
-- Project: tonal-land-477206-h3
-- Dataset: stock_data
-- ============================================

-- ============================================
-- Chart 1: Foreign/Institution Net Buy vs Volume
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_investor_volume` AS
SELECT 
  date AS date_kr,
  ticker,
  name,
  market_cap,
  foreign_net_buy,
  institution_net_buy,
  volume,
  SAFE_DIVIDE(foreign_net_buy * 10000, close * volume) AS foreign_ratio,
  SAFE_DIVIDE(institution_net_buy * 10000, close * volume) AS institution_ratio
FROM `tonal-land-477206-h3.stock_data.daily_metrics`
WHERE volume > 0
ORDER BY date DESC, market_cap DESC NULLS LAST, ticker;

-- ============================================
-- Chart 2: Bollinger Bands + Close Price
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_bollinger_price` AS
SELECT 
  date AS date_kr,
  ticker,
  name,
  market_cap,
  close,
  bb_upper,
  bb_lower,
  bb_position,
  ma20
FROM `tonal-land-477206-h3.stock_data.daily_metrics`
WHERE bb_upper IS NOT NULL
ORDER BY date DESC, market_cap DESC NULLS LAST, ticker;

-- ============================================
-- Chart 3: Short Balance
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_short_balance` AS
SELECT 
  date AS date_kr,
  ticker,
  name,
  market_cap,
  short_balance,
  short_balance_diff,
  SAFE_DIVIDE(short_balance, volume) AS short_ratio
FROM `tonal-land-477206-h3.stock_data.daily_metrics`
WHERE short_balance IS NOT NULL
ORDER BY date DESC, market_cap DESC NULLS LAST, ticker;

-- ============================================
-- Chart 4: OBV + RSI
-- ============================================
CREATE OR REPLACE VIEW `tonal-land-477206-h3.stock_data.v_obv_rsi` AS
SELECT 
  date AS date_kr,
  ticker,
  name,
  market_cap,
  obv,
  rsi,
  rsi_change,
  close
FROM `tonal-land-477206-h3.stock_data.daily_metrics`
WHERE obv IS NOT NULL AND rsi IS NOT NULL
ORDER BY date DESC, market_cap DESC NULLS LAST, ticker;

