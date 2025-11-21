import os
import json
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import config

class BigQueryClient:
    def __init__(self):
        self.client = bigquery.Client(project=config.PROJECT_ID)
        self.dataset_id = f"{config.PROJECT_ID}.{config.BQ_DATASET_NAME}"
        self.table_id = config.BQ_TABLE_ID

    def create_dataset_if_not_exists(self):
        """Create the dataset if it doesn't exist."""
        try:
            self.client.get_dataset(self.dataset_id)
            print(f"Dataset {self.dataset_id} already exists.")
        except NotFound:
            dataset = bigquery.Dataset(self.dataset_id)
            dataset.location = "us-central1"  # Use the same region as Cloud Run if possible
            dataset = self.client.create_dataset(dataset, timeout=30)
            print(f"Created dataset {self.dataset_id}")

    def create_table_if_not_exists(self):
        """Create the table if it doesn't exist, using the schema file."""
        try:
            self.client.get_table(self.table_id)
            print(f"Table {self.table_id} already exists.")
        except NotFound:
            schema = self._load_schema()
            table = bigquery.Table(self.table_id, schema=schema)
            
            # Partitioning by date
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="date"
            )
            
            # Clustering by ticker
            table.clustering_fields = ["ticker"]
            
            table = self.client.create_table(table)
            print(f"Created table {self.table_id}")

    def _load_schema(self):
        """Load schema from JSON file."""
        with open(config.SCHEMA_PATH, "r") as f:
            schema_json = json.load(f)
        return [bigquery.SchemaField.from_api_repr(field) for field in schema_json]

    def update_schema_if_needed(self):
        """Check if new columns need to be added to the table based on the schema file."""
        try:
            table = self.client.get_table(self.table_id)
            existing_fields = {field.name for field in table.schema}
            
            target_schema = self._load_schema()
            new_fields = []
            
            for field in target_schema:
                if field.name not in existing_fields:
                    new_fields.append(field)
            
            if new_fields:
                original_schema = table.schema
                new_schema = original_schema[:] + new_fields
                table.schema = new_schema
                self.client.update_table(table, ["schema"])
                print(f"Added new columns to {self.table_id}: {[f.name for f in new_fields]}")
            else:
                print("Schema is up to date.")
                
        except NotFound:
            print("Table not found, skipping schema update.")

    def upload_dataframe(self, df: pd.DataFrame):
        """Upload DataFrame to BigQuery."""
        if df.empty:
            print("DataFrame is empty, skipping upload.")
            return

        # Map columns to BigQuery schema names
        column_mapping = {
            "날짜": "date",
            "티커": "ticker",
            "종목명": "name",
            "종가": "close",
            "종가전일비": "close_diff",
            "거래량": "volume",
            "거래량전일비": "volume_diff",
            "개인순매수": "individual_net_buy",
            "외국인순매수": "foreign_net_buy",
            "기관순매수": "institution_net_buy",
            "대차잔고": "short_balance",
            "대차잔고전일비": "short_balance_diff",
            "PER": "per",
            "EPS": "eps",
            "추정EPS": "estimated_eps",
            "PBR": "pbr",
            "BPS": "bps"
        }
        
        # Rename columns
        df_upload = df.rename(columns=column_mapping)
        
        # Ensure all schema columns exist in DataFrame (fill with None if missing)
        schema = self._load_schema()
        schema_columns = [field.name for field in schema]
        
        for col in schema_columns:
            if col not in df_upload.columns:
                df_upload[col] = None
                
        # Select only columns present in schema to avoid errors with extra columns
        df_upload = df_upload[schema_columns]
        
        # Convert date column to datetime objects if it's string
        if "date" in df_upload.columns and df_upload["date"].dtype == "object":
             df_upload["date"] = pd.to_datetime(df_upload["date"]).dt.date

        # Configure job
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            write_disposition="WRITE_APPEND",
        )

        job = self.client.load_table_from_dataframe(
            df_upload, self.table_id, job_config=job_config
        )
        
        job.result()  # Wait for the job to complete.
        print(f"Loaded {job.output_rows} rows to {self.table_id}")

    def get_latest_date(self, ticker: str):
        """Get the latest date for a specific ticker in the table."""
        query = f"""
            SELECT MAX(date) as max_date
            FROM `{self.table_id}`
            WHERE ticker = @ticker
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker)
            ]
        )
        try:
            result = self.client.query(query, job_config=job_config).result()
            row = next(result)
            return row.max_date
        except Exception as e:
            print(f"Error querying latest date: {e}")
            return None
