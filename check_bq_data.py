from bigquery_client import BigQueryClient
import config

def check_data():
    bq_client = BigQueryClient()
    query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(bb_upper) as bb_cnt,
            COUNT(rsi) as rsi_cnt,
            COUNT(obv) as obv_cnt,
            COUNT(short_balance) as short_cnt
        FROM `{config.PROJECT_ID}.{config.BQ_DATASET_NAME}.daily_metrics`
    """
    
    try:
        query_job = bq_client.client.query(query)
        results = query_job.result()
        for row in results:
            print(f"Total rows: {row.total}")
            print(f"Rows with Bollinger Bands: {row.bb_cnt}")
            print(f"Rows with RSI: {row.rsi_cnt}")
            print(f"Rows with OBV: {row.obv_cnt}")
            print(f"Rows with Short Balance: {row.short_cnt}")
    except Exception as e:
        print(f"Error checking data: {e}")

if __name__ == "__main__":
    check_data()
