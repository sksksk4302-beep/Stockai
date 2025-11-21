import os

# Google Cloud Project ID
# Cloud Functions/Run usually provide this in 'GOOGLE_CLOUD_PROJECT' env var
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "tonal-land-477206-h3")

# BigQuery Settings
BQ_DATASET_NAME = "stock_data"
BQ_TABLE_NAME = "daily_metrics"
BQ_TABLE_ID = f"{PROJECT_ID}.{BQ_DATASET_NAME}.{BQ_TABLE_NAME}"

# Schema File Path
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema", "stock_daily_schema.json")
