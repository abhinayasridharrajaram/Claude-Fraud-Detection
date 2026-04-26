"""
00_build_features.py
Build and save the shared feature matrix used by all downstream ML scripts.
Outputs: outputs/ml/features.parquet
"""

import sys
import numpy as np
import pandas as pd
import duckdb
from sklearn.preprocessing import StandardScaler
import pyarrow as pa
import pyarrow.parquet as pq
import os

# -- paths ----------------------------------------------------------------------
BASE = r"C:\Users\Abhi\claude-bigquery-copilot"
DATA_CSV = f"{BASE}/data/creditcard.csv"
OUT_DIR  = f"{BASE}/outputs/ml"
os.makedirs(OUT_DIR, exist_ok=True)

# -- load ----------------------------------------------------------------------?
print("Loading data via DuckDB ?")
con = duckdb.connect()
df  = con.execute(f"SELECT * FROM '{DATA_CSV}'").df()
con.close()

EXPECTED_ROWS = 284_807
if len(df) != EXPECTED_ROWS:
    sys.exit(f"ERROR: expected {EXPECTED_ROWS} rows, got {len(df)}")
print(f"Row count verified: {len(df)}")

# -- feature engineering --------------------------------------------------------
df["log_amount"] = np.log1p(df["Amount"])
df["hour_of_day"] = (df["Time"] % 86400) / 3600.0
df["day"]         = (df["Time"] // 86400).astype(int)

feature_cols = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]

scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[feature_cols])

# -- save ----------------------------------------------------------------------?
feat_df = pd.DataFrame(X_scaled, columns=feature_cols)
feat_df["Class"] = df["Class"].values
feat_df["day"]   = df["day"].values

out_path = f"{OUT_DIR}/features.parquet"
feat_df.to_parquet(out_path, index=True)
print(f"Saved feature matrix -> {out_path}  shape={feat_df.shape}")
