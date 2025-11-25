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
    for i, rule in enumerate(best_rules, 1):
        rule_str = engine.decode_rule(rule)
        fitness = rule.fitness.values[0]
        print(f"{i}. {rule_str} \t(Total Return: {fitness:.2f}%)")
    print("-" * 50)
    
    print("\n💡 Interpretation:")
    print("These rules represent conditions that historically led to positive returns.")
    print("Example: 'rsi < 30.0' means buying when RSI is below 30 yielded profit.")

if __name__ == "__main__":
    main()
