import os
import pandas as pd
from google.cloud import bigquery
from datetime import datetime, timedelta

class DataLoader:
    def __init__(self, project_id=None, dataset_id="stock_data", table_id="stock_daily"):
        # Use env var if project_id not provided
        if not project_id:
            project_id = os.getenv('PROJECT_ID', 'tonal-land-477206-h3')
            
        self.client = bigquery.Client(project=project_id)
        self.table_ref = f"{project_id}.{dataset_id}.{table_id}"
        print(f"🔌 Connecting to BigQuery table: {self.table_ref}")
        
        # Debug: List datasets and tables to verify existence
        try:
            print(f"🔍 Checking datasets in project {project_id}...")
            datasets = list(self.client.list_datasets())
            if datasets:
                print(f"  Found {len(datasets)} datasets: {[d.dataset_id for d in datasets]}")
                for ds in datasets:
                    if ds.dataset_id == dataset_id:
                        tables = list(self.client.list_tables(ds.dataset_id))
                        print(f"  Tables in {dataset_id}: {[t.table_id for t in tables]}")
            else:
                print("  ⚠️ No datasets found!")
        except Exception as e:
            print(f"  ⚠️ Error listing datasets: {e}")
        
        self.cache_dir = "data_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def fetch_data(self, ticker=None, days=365, use_cache=True):
        """
        Fetches stock data from BigQuery or local cache.
        """
        today = datetime.now().strftime("%Y%m%d")
        cache_file = os.path.join(self.cache_dir, f"stock_data_{today}.parquet")
        
        if use_cache and os.path.exists(cache_file):
            print(f"Loading data from cache: {cache_file}")
            df = pd.read_parquet(cache_file)
            if ticker:
                df = df[df['ticker'] == ticker]
            return df

        try:
            print("Fetching data from BigQuery...")
            query = f"""
                SELECT *
                FROM `{self.table_ref}`
                WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
            """
            
            if ticker:
                query += f" AND ticker = '{ticker}'"
                
            query += " ORDER BY ticker, date"
            
            df = self.client.query(query).to_dataframe()
            
            # Convert date to datetime
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                
            # Save to cache if fetching all data
            if not ticker and use_cache:
                print(f"Saving data to cache: {cache_file}")
                df.to_parquet(cache_file)
                
            return df
            
        except Exception as e:
            print(f"⚠️ BigQuery connection failed: {e}")
            print("🔄 Generating MOCK data for testing...")
            return self._generate_mock_data(days)

    def _generate_mock_data(self, days):
        """Generates random stock data for testing"""
        import numpy as np
        
        dates = pd.date_range(end=datetime.now(), periods=days)
        data = []
        
        for ticker in ['005930', '000660', '035420']: # Samsung, SK Hynix, Naver
            # Random walk price
            price = 10000 + np.cumsum(np.random.randn(days) * 100)
            
            # Features
            rsi = np.random.uniform(20, 80, days)
            ma5 = price + np.random.randn(days) * 50
            ma20 = price + np.random.randn(days) * 100
            
            # Target (Next day return)
            target = np.random.normal(0, 2, days) # Mean 0, Std 2%
            
            # Create correlation: Low RSI -> Higher return (to see if GA finds it)
            target += (30 - rsi) * 0.1 # If RSI is 20, add 1% return
            
            for i in range(days):
                data.append({
                    'date': dates[i],
                    'ticker': ticker,
                    'close': price[i],
                    'rsi': rsi[i],
                    'ma5': ma5[i],
                    'ma20': ma20[i],
                    'target_return_1d': target[i]
                })
                
        return pd.DataFrame(data)

    def get_tickers(self):
        """Returns list of unique tickers available in the data"""
        query = f"SELECT DISTINCT ticker, name FROM `{self.table_ref}`"
        return self.client.query(query).to_dataframe()

if __name__ == "__main__":
    loader = DataLoader()
    df = loader.fetch_data(days=30, use_cache=False)
    print(f"Loaded {len(df)} rows")
    print(df.head())
