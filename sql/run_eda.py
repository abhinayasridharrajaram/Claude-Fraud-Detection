"""
run_eda.py — Execute all EDA SQL queries in order, save parquet outputs,
             and print a full results dump for narrative writing.

Run from project root:
    python sql/run_eda.py
"""

import os
import sys
import duckdb
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)  # all relative paths (data/creditcard.csv) work from here

OUT = os.path.join(BASE, "outputs", "eda")
os.makedirs(OUT, exist_ok=True)

CSV = "data/creditcard.csv"

def q(sql):
    return duckdb.connect().execute(sql).df()

def sep(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

# ── 1. Schema & shape ────────────────────────────────────────────────────────
sep("01  SCHEMA & SHAPE")

shape_df = q(f"""
    SELECT column_name, column_type AS data_type
    FROM (DESCRIBE SELECT * FROM '{CSV}')
""")
row_count = q(f"SELECT COUNT(*) AS n FROM '{CSV}'")['n'][0]
disk_bytes = os.path.getsize(os.path.join(BASE, CSV))

print(shape_df.to_string(index=False))
print(f"\nRow count : {row_count:,}")
print(f"Disk size : {disk_bytes / 1_048_576:.1f} MB  ({disk_bytes:,} bytes)")

shape_df.to_parquet(os.path.join(OUT, "01_schema.parquet"), index=False)

# ── 2. Class balance ─────────────────────────────────────────────────────────
sep("02  CLASS BALANCE")

balance_df = q(f"""
    SELECT
        Class,
        COUNT(*)                                              AS n,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 4)   AS pct
    FROM '{CSV}'
    GROUP BY Class
    ORDER BY Class
""")
print(balance_df.to_string(index=False))
balance_df.to_parquet(os.path.join(OUT, "02_class_balance.parquet"), index=False)

# ── 3. Time coverage ─────────────────────────────────────────────────────────
sep("03  TIME COVERAGE")

time_df = q(f"""
    SELECT
        MIN(Time)                              AS time_min_sec,
        MAX(Time)                              AS time_max_sec,
        ROUND((MAX(Time) - MIN(Time)) / 3600.0, 2) AS span_hours
    FROM '{CSV}'
""")
print(time_df.to_string(index=False))

hour_df = q(f"""
    SELECT
        CAST(FLOOR((Time % 86400) / 3600) AS INTEGER) AS hour_of_day,
        COUNT(*)                                       AS total,
        SUM(Class)                                     AS fraud_count,
        ROUND(100.0 * SUM(Class) / COUNT(*), 4)        AS fraud_rate_pct
    FROM '{CSV}'
    GROUP BY hour_of_day
    ORDER BY hour_of_day
""")
print("\nFraud rate by hour_of_day:")
print(hour_df.to_string(index=False))

time_df.to_parquet(os.path.join(OUT, "03_time_coverage.parquet"), index=False)
hour_df.to_parquet(os.path.join(OUT, "04_fraud_by_hour.parquet"), index=False)

# ── 4. Amount distribution ───────────────────────────────────────────────────
sep("04  AMOUNT DISTRIBUTION")

amt_df = q(f"""
    SELECT
        Class,
        COUNT(*)                                       AS n,
        ROUND(QUANTILE_CONT(Amount, 0.01),  2)         AS p01,
        ROUND(QUANTILE_CONT(Amount, 0.10),  2)         AS p10,
        ROUND(QUANTILE_CONT(Amount, 0.50),  2)         AS p50,
        ROUND(QUANTILE_CONT(Amount, 0.90),  2)         AS p90,
        ROUND(QUANTILE_CONT(Amount, 0.99),  2)         AS p99,
        ROUND(QUANTILE_CONT(Amount, 0.999), 2)         AS p999,
        ROUND(AVG(Amount), 2)                          AS mean,
        ROUND(STDDEV(Amount), 2)                       AS stddev,
        ROUND(MAX(Amount), 2)                          AS max_val
    FROM '{CSV}'
    GROUP BY Class
    ORDER BY Class
""")
print(amt_df.to_string(index=False))

zero_df = q(f"""
    SELECT
        COUNT(*)                                    AS zero_amount_count,
        SUM(Class)                                  AS fraud_in_zero,
        ROUND(100.0 * SUM(Class) / COUNT(*), 4)    AS fraud_rate_pct
    FROM '{CSV}'
    WHERE Amount = 0
""")
print("\nZero-amount transactions:")
print(zero_df.to_string(index=False))

amt_df.to_parquet(os.path.join(OUT, "05_amount_quantiles.parquet"), index=False)
zero_df.to_parquet(os.path.join(OUT, "06_zero_amount.parquet"), index=False)

# ── 5. Feature ranges V1-V28 ─────────────────────────────────────────────────
sep("05  FEATURE RANGES  V1-V28")

feat_sql = " UNION ALL ".join([
    f"SELECT 'V{i}' AS feature, MIN(V{i}) AS mn, MAX(V{i}) AS mx, "
    f"AVG(V{i}) AS avg_val, STDDEV(V{i}) AS sd FROM '{CSV}'"
    for i in range(1, 29)
])
feat_df = q(f"""
    SELECT feature,
           ROUND(mn, 4)      AS min_val,
           ROUND(mx, 4)      AS max_val,
           ROUND(avg_val, 6) AS mean,
           ROUND(sd, 4)      AS stddev,
           CASE WHEN ABS(avg_val) > 0.1 THEN 'FLAG' ELSE 'ok' END AS mean_flag
    FROM ({feat_sql}) t
    ORDER BY feature
""")
print(feat_df.to_string(index=False))

flagged = feat_df[feat_df['mean_flag'] == 'FLAG']
if flagged.empty:
    print("\nNo features flagged (all |mean| <= 0.1).")
else:
    print(f"\nFlagged features (|mean| > 0.1):\n{flagged.to_string(index=False)}")

feat_df.to_parquet(os.path.join(OUT, "07_feature_ranges.parquet"), index=False)

# ── 6. Correlation with Class ─────────────────────────────────────────────────
sep("06  CORRELATION WITH CLASS")

corr_sql = " UNION ALL ".join([
    f"SELECT 'V{i}' AS feature, CORR(V{i}, Class) AS corr_val FROM '{CSV}'"
    for i in range(1, 29)
]) + f" UNION ALL SELECT 'Amount', CORR(Amount, Class) FROM '{CSV}'"

corr_df = q(f"""
    SELECT feature,
           ROUND(corr_val, 6)       AS corr_with_class,
           ROUND(ABS(corr_val), 6)  AS abs_corr
    FROM ({corr_sql}) t
    ORDER BY abs_corr DESC
""")
print("All correlations (sorted by |corr|):")
print(corr_df.to_string(index=False))
print("\nTop 6 by absolute correlation:")
print(corr_df.head(6).to_string(index=False))

corr_df.to_parquet(os.path.join(OUT, "08_correlations.parquet"), index=False)

print("\n\nAll outputs saved to:", OUT)
