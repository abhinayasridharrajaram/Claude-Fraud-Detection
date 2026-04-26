"""
run_full_eda.py
Run all EDA SQL queries in order, save parquet outputs, compute normalized
mean-difference separation scores, and emit results as JSON for report generation.

Usage:
    python sql/run_full_eda.py
"""

import os
import sys
import json
import duckdb
import pandas as pd
import numpy as np

# Always work from the project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_ROOT)

OUT_DIR = os.path.join(PROJECT_ROOT, "outputs", "eda")
os.makedirs(OUT_DIR, exist_ok=True)

CSV = "data/creditcard.csv"

def q(sql: str) -> pd.DataFrame:
    con = duckdb.connect()
    return con.execute(sql).df()


def save(df: pd.DataFrame, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    if name.endswith(".parquet"):
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)
    return path


results = {}

# ------------------------------------------------------------------
# 01  Schema & shape
# ------------------------------------------------------------------
print("=== 01 Schema & shape ===")
schema_df = q(f"DESCRIBE SELECT * FROM '{CSV}' LIMIT 1")
row_count = q(f"SELECT COUNT(*) AS n FROM '{CSV}'").iloc[0, 0]
disk_bytes = os.path.getsize(os.path.join(PROJECT_ROOT, CSV))
save(schema_df, "01_schema.parquet")
print(schema_df.to_string(index=False))
print(f"\nRow count : {row_count:,}")
print(f"Disk size : {disk_bytes / 1e6:.1f} MB")
results["row_count"] = int(row_count)
results["disk_mb"]   = round(disk_bytes / 1e6, 1)
results["columns"]   = list(schema_df["column_name"])

# ------------------------------------------------------------------
# 02  Class balance
# ------------------------------------------------------------------
print("\n=== 02 Class balance ===")
balance_df = q(open("sql/02_class_balance.sql").read())
save(balance_df, "02_class_balance.parquet")
print(balance_df.to_string(index=False))
fraud_row  = balance_df[balance_df["Class"] == 1].iloc[0]
results["n_fraud"]      = int(fraud_row["n_rows"])
results["fraud_pct"]    = float(fraud_row["pct"])
results["n_legit"]      = int(balance_df[balance_df["Class"] == 0].iloc[0]["n_rows"])

# ------------------------------------------------------------------
# 03  Time coverage
# ------------------------------------------------------------------
print("\n=== 03 Time coverage ===")
time_df = q(open("sql/03_time_coverage.sql").read())
print(time_df.to_string(index=False))
results["min_time_sec"] = float(time_df["min_time_sec"].iloc[0])
results["max_time_sec"] = float(time_df["max_time_sec"].iloc[0])
results["span_hours"]   = float(time_df["span_hours"].iloc[0])

# ------------------------------------------------------------------
# 04  Fraud rate by hour_of_day
# ------------------------------------------------------------------
print("\n=== 04 Fraud rate by hour_of_day ===")
hour_df = q(open("sql/04_fraud_by_hour.sql").read())
save(hour_df, "04_fraud_by_hour.parquet")
print(hour_df.to_string(index=False))
peak_hour_row = hour_df.sort_values("fraud_rate_pct", ascending=False).iloc[0]
results["peak_fraud_hour"]      = int(peak_hour_row["hour_of_day"])
results["peak_fraud_rate_pct"]  = float(peak_hour_row["fraud_rate_pct"])

# ------------------------------------------------------------------
# 10  Fraud rate by day
# ------------------------------------------------------------------
print("\n=== 10 Fraud rate by day ===")
day_df = q(open("sql/10_fraud_by_day.sql").read())
save(day_df, "10_fraud_by_day.parquet")
print(day_df.to_string(index=False))
results["fraud_by_day"] = day_df.to_dict(orient="records")

# ------------------------------------------------------------------
# 05  Amount quantiles
# ------------------------------------------------------------------
print("\n=== 05 Amount quantiles ===")
quant_df = q(open("sql/05_amount_quantiles.sql").read())
save(quant_df, "05_amount_quantiles.parquet")
print(quant_df.to_string(index=False))
legit_q  = quant_df[quant_df["Class"] == 0].iloc[0]
fraud_q  = quant_df[quant_df["Class"] == 1].iloc[0]
results["legit_amount_median"] = float(legit_q["p50"])
results["fraud_amount_median"] = float(fraud_q["p50"])
results["legit_amount_mean"]   = float(legit_q["mean_amount"])
results["fraud_amount_mean"]   = float(fraud_q["mean_amount"])
results["legit_amount_max"]    = float(legit_q["max_amount"])
results["fraud_amount_max"]    = float(fraud_q["max_amount"])

# ------------------------------------------------------------------
# 06  Zero-amount transactions
# ------------------------------------------------------------------
print("\n=== 06 Zero-amount transactions ===")
zero_df = q(open("sql/06_zero_amount.sql").read())
print(zero_df.to_string(index=False))
results["n_zero_amount"]       = int(zero_df["n_zero_amount"].iloc[0])
results["zero_amount_fraud_n"] = int(zero_df["n_fraud"].iloc[0])
results["zero_amount_fraud_pct"] = float(zero_df["fraud_rate_pct"].iloc[0])

# ------------------------------------------------------------------
# 07  Feature ranges (V1-V28 + derived)
# ------------------------------------------------------------------
print("\n=== 07 Feature ranges ===")
feat_df = q(open("sql/07_feature_ranges.sql").read())
save(feat_df, "07_feature_ranges.parquet")
flagged = feat_df[feat_df["mean_flag"] == "FLAG"]["feature"].tolist()
print(feat_df.to_string(index=False))
print(f"\nFeatures with |mean| > 0.1: {flagged if flagged else 'none'}")
results["features_flagged_mean"] = flagged

# ------------------------------------------------------------------
# 08  Correlations with Class
# ------------------------------------------------------------------
print("\n=== 08 Correlations with Class ===")
corr_df = q(open("sql/08_correlation_with_class.sql").read())
save(corr_df, "08_correlations.parquet")
top6 = corr_df.head(6)
print("Top 6 by |correlation|:")
print(top6.to_string(index=False))
results["top6_corr"] = top6.to_dict(orient="records")

# ------------------------------------------------------------------
# 09  Per-class distributions (for normalized mean-diff)
# ------------------------------------------------------------------
print("\n=== 09 Normalized mean-difference (separation scores) ===")
dist_df = q(open("sql/09_fraud_distributions.sql").read())
save(dist_df, "09_fraud_distributions.parquet")

legit_row = dist_df[dist_df["Class"] == 0].iloc[0]
fraud_row_d = dist_df[dist_df["Class"] == 1].iloc[0]

features_vx = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]
sep_records = []
for feat in features_vx:
    mu0 = legit_row[f"{feat}_mean"]
    mu1 = fraud_row_d[f"{feat}_mean"]
    s0  = legit_row[f"{feat}_std"]
    s1  = fraud_row_d[f"{feat}_std"]
    pooled_std = np.sqrt((s0**2 + s1**2) / 2)
    sep = abs(mu1 - mu0) / pooled_std if pooled_std > 0 else 0.0
    sep_records.append({
        "feature": feat,
        "mean_legit": round(float(mu0), 6),
        "mean_fraud":  round(float(mu1), 6),
        "mean_diff":   round(float(mu1 - mu0), 6),
        "pooled_std":  round(float(pooled_std), 6),
        "sep_score":   round(float(sep), 6),
    })

sep_df = pd.DataFrame(sep_records).sort_values("sep_score", ascending=False)
save(sep_df, "09_separation_scores.parquet")
print(sep_df.head(10).to_string(index=False))

top1_feat = sep_df.iloc[0]
results["top_discriminating_feature"] = top1_feat["feature"]
results["top_sep_score"]              = float(top1_feat["sep_score"])
results["top_mean_diff"]              = float(top1_feat["mean_diff"])
results["top6_sep"] = sep_df.head(6).to_dict(orient="records")

# ------------------------------------------------------------------
# Persist results JSON for report builder
# ------------------------------------------------------------------
json_path = os.path.join(OUT_DIR, "eda_results.json")
with open(json_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults JSON saved to {json_path}")

print("\n=== EDA complete ===")
print(f"Top discriminating feature: {results['top_discriminating_feature']}, "
      f"sep_score = {results['top_sep_score']:.4f}, "
      f"fraud mean - legit mean = {results['top_mean_diff']:.4f}")
