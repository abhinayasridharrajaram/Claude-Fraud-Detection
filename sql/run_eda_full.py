"""
run_eda_full.py
Run all EDA SQL queries in order, save parquet outputs, print results.
Usage: python sql/run_eda_full.py
"""

import os
import sys
import duckdb
import pandas as pd

# Always work from project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

OUT_DIR = "outputs/eda"
os.makedirs(OUT_DIR, exist_ok=True)

SQL_DIR = "sql"

QUERIES = [
    ("01_schema_shape",       "sql/01_schema_shape.sql",       None),
    ("02_class_balance",      "sql/02_class_balance.sql",      f"{OUT_DIR}/02_class_balance.parquet"),
    ("03_time_coverage",      "sql/03_time_coverage.sql",      f"{OUT_DIR}/03_time_coverage.parquet"),
    ("04_fraud_by_hour",      "sql/04_fraud_by_hour.sql",      f"{OUT_DIR}/04_fraud_by_hour.parquet"),
    ("05_amount_quantiles",   "sql/05_amount_quantiles.sql",   f"{OUT_DIR}/05_amount_quantiles.parquet"),
    ("06_zero_amount",        "sql/06_zero_amount.sql",        f"{OUT_DIR}/06_zero_amount.parquet"),
    ("07_feature_ranges",     "sql/07_feature_ranges.sql",     f"{OUT_DIR}/07_feature_ranges.parquet"),
    ("08_correlation_with_class", "sql/08_correlation_with_class.sql", f"{OUT_DIR}/08_correlations.parquet"),
]

results = {}

for name, sql_path, save_path in QUERIES:
    print(f"\n{'='*60}")
    print(f"Running: {name}")
    print(f"{'='*60}")
    sql = open(sql_path).read()
    con = duckdb.connect()
    df = con.execute(sql).df()
    con.close()
    results[name] = df

    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 140)
    pd.set_option("display.float_format", "{:.6f}".format)
    print(df.to_string(index=False))

    if save_path:
        df.to_parquet(save_path, index=False)
        print(f"  -> Saved: {save_path}")

print("\nAll queries completed.")
