import sys
import os
import pandas as pd
from data_loader import DataLoader
from ga_engine import GAEngine

def main():
    print("🚀 Starting Genetic Algorithm Strategy Engine...")
    
    # 1. Load Data
    loader = DataLoader()
    # Fetch 1 year of data
    df = loader.fetch_data(days=365)
    
    if df.empty:
        print("❌ No data found. Please run the collection bot first.")
        return

    print(f"✅ Loaded {len(df)} rows of data.")
    
    # 2. Preprocessing
    # Filter out rows with missing target or features
    df = df.dropna(subset=['target_return_1d'])
    
    # Select numeric columns only for GA
    numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
    df_numeric = df[numeric_cols].copy()
    
    # Fill remaining NaNs with 0 or mean (simple handling for now)
    df_numeric = df_numeric.fillna(0)
    
    print(f"📊 Features available: {len(df_numeric.columns)}")
    
    # 3. Run GA
    print("\n🧬 Evolving trading rules...")
    engine = GAEngine(df_numeric)
    
    # Run for 20 generations with 100 population
    best_rules, log = engine.run(generations=20, population_size=100)
    
    # 4. Report Results
    print("\n🏆 Top Discovered Rules:")
    print("-" * 50)
    
    discovered_rules = []
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    
    for i, rule in enumerate(best_rules, 1):
        rule_str = engine.decode_rule(rule)
        fitness = rule.fitness.values[0]
        print(f"{i}. {rule_str} \t(Total Return: {fitness:.2f}%)")
        
        discovered_rules.append({
            'date': today,
            'rank': i,
            'rule_expression': rule_str,
            'expected_return': float(fitness),
            'num_conditions': len(rule)
        })
    print("-" * 50)
    
    # 5. Save to BigQuery
    save_to_bq(discovered_rules)

def save_to_bq(rules):
    """Saves discovered rules to BigQuery"""
    if not rules:
        return

    print("\n💾 Saving rules to BigQuery (strategy_rules table)...")
    try:
        from google.cloud import bigquery
        client = bigquery.Client()
        table_id = "tonal-land-477206-h3.stock_data.strategy_rules"
        
        # Define schema
        schema = [
            bigquery.SchemaField("date", "DATE"),
            bigquery.SchemaField("rank", "INTEGER"),
            bigquery.SchemaField("rule_expression", "STRING"),
            bigquery.SchemaField("expected_return", "FLOAT"),
            bigquery.SchemaField("num_conditions", "INTEGER"),
        ]
        
        # Create table if not exists
        try:
            client.get_table(table_id)
        except:
            print(f"Creating new table: {table_id}")
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)
            
        # Insert rows
        errors = client.insert_rows_json(table_id, rules)
        if errors:
            print(f"⚠️ Errors inserting rows: {errors}")
        else:
            print("✅ Rules saved successfully!")
            
    except Exception as e:
        print(f"⚠️ Failed to save to BigQuery: {e}")


if __name__ == "__main__":
    main()
