"""
run_eda_creditcard.py
Run all EDA SQL queries for the creditcard dataset and save outputs.
"""
import os
import sys
import duckdb
import pandas as pd

PROJECT_ROOT = r"C:\Users\Abhi\claude-bigquery-copilot"
SQL_DIR      = os.path.join(PROJECT_ROOT, "sql")
OUT_DIR      = os.path.join(PROJECT_ROOT, "outputs", "eda")
os.makedirs(OUT_DIR, exist_ok=True)

def run(sql_file, save_name=None):
    path = os.path.join(SQL_DIR, sql_file)
    sql  = open(path).read()
    con  = duckdb.connect()
    con.execute(f"SET FILE_SEARCH_PATH='{PROJECT_ROOT}'")
    os.chdir(PROJECT_ROOT)
    df   = con.execute(sql).df()
    if save_name:
        out = os.path.join(OUT_DIR, save_name)
        if out.endswith(".parquet"):
            df.to_parquet(out, index=False)
        else:
            df.to_csv(out, index=False)
        print(f"  saved -> {out}")
    return df

pd.set_option("display.max_columns", 40)
pd.set_option("display.width", 160)
pd.set_option("display.float_format", "{:.4f}".format)

print("=== 01 Schema & shape ===")
df01 = run("01_schema_shape.sql", "01_schema_shape.parquet")
print(df01.to_string(index=False))

print("\n=== 02 Class balance ===")
df02 = run("02_class_balance.sql", "02_class_balance.parquet")
print(df02.to_string(index=False))

print("\n=== 03 Time coverage ===")
df03 = run("03_time_coverage.sql", "03_time_coverage.parquet")
print(df03.to_string(index=False))

print("\n=== 04 Fraud by hour ===")
df04 = run("04_fraud_by_hour.sql", "04_fraud_by_hour.parquet")
print(df04.to_string(index=False))

print("\n=== 05 Amount quantiles ===")
df05 = run("05_amount_quantiles.sql", "05_amount_quantiles.parquet")
print(df05.to_string(index=False))

print("\n=== 06 Zero-amount transactions ===")
df06 = run("06_zero_amount.sql", "06_zero_amount.parquet")
print(df06.to_string(index=False))

print("\n=== 07 Feature ranges ===")
df07 = run("07_feature_ranges.sql", "07_feature_ranges.parquet")
print(df07.to_string(index=False))

print("\n=== 08 Correlation with Class ===")
df08 = run("08_correlation_with_class.sql", "08_correlation_with_class.parquet")
print(df08.to_string(index=False))

print("\nAll queries complete.")
