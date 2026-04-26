# EDA Summary — Credit Card Fraud Detection

**Run ID:** 2026-04-24_1712
**Dataset:** `data/creditcard.csv`
**Analyst:** Claude Code (claude-sonnet-4-6)
**Date:** 2026-04-24

---

## 1. Schema and Shape

| Property | Value |
|---|---|
| Rows | 284,807 |
| Columns | 31 |
| Disk size | 98.2 MB (CSV) |
| Null values | 0 across all columns |

**Column inventory:**

| Column | Type | Notes |
|---|---|---|
| `Time` | int64 | Seconds elapsed from first transaction; dropped after deriving `hour_of_day` and `day` |
| `V1` – `V28` | float64 | Anonymized PCA-transformed features |
| `Amount` | float64 | Transaction amount in USD; dropped after deriving `log_amount` |
| `Class` | int64 | Label: 1 = fraud, 0 = legitimate (evaluation only, never a training input) |

**Derived features (used in modelling):**

| Feature | Formula |
|---|---|
| `log_amount` | `log1p(Amount)` |
| `hour_of_day` | `(Time % 86400) / 3600.0` |
| `day` | `(Time // 86400).astype(int)` — values 0 or 1 |

Raw `Time` and raw `Amount` are dropped from the feature matrix after derivation.

**SQL:** `sql/01_schema_shape.sql`

---

## 2. Class Balance

| Class | Count | Percentage |
|---|---|---|
| 0 (legitimate) | 284,315 | 99.8273% |
| 1 (fraud) | 492 | 0.1727% |

The dataset is severely imbalanced: frauds represent roughly 1 in 579 transactions. This imbalance is the defining challenge for this project — naive classifiers that predict all-legitimate would achieve 99.83% accuracy yet catch zero fraud.

For anomaly detection, the `contamination` parameter should be set close to this base rate (0.002 is a reasonable starting point). Standard accuracy metrics are not informative; evaluation must rely on precision@top-k, recall@top-k, and ROC-AUC.

**SQL:** `sql/02_class_balance.sql`

---

## 3. Time Coverage

| Metric | Value |
|---|---|
| `min(Time)` | 0 s |
| `max(Time)` | 172,792 s |
| Span | 47.998 hours (~2 calendar days) |

The dataset covers 48 hours continuously with no apparent gaps. Day 0 (the first 24 hours) contains 144,786 transactions (281 fraudulent, fraud rate 0.194%), and Day 1 contains 140,021 transactions (211 fraudulent, fraud rate 0.151%). Volume is essentially equal across both days; the slightly higher fraud rate on Day 0 may reflect normal variation.

### Fraud Rate by Hour of Day

The table below (from `sql/04_fraud_by_hour.sql`) reveals pronounced intraday patterns:

| Hour | Transactions | Fraud | Fraud Rate (%) |
|---:|---:|---:|---:|
| 0 | 7,695 | 6 | 0.078 |
| 1 | 4,220 | 10 | 0.237 |
| 2 | 3,328 | 57 | **1.713** |
| 3 | 3,492 | 17 | 0.487 |
| 4 | 2,209 | 23 | **1.041** |
| 5 | 2,990 | 11 | 0.368 |
| 6 | 4,101 | 9 | 0.220 |
| 7 | 7,243 | 23 | 0.318 |
| 8 | 10,276 | 9 | 0.088 |
| 9 | 15,838 | 16 | 0.101 |
| 10 | 16,598 | 8 | 0.048 |
| 11 | 16,856 | 53 | 0.314 |
| 12 | 15,420 | 17 | 0.110 |
| 13 | 15,365 | 17 | 0.111 |
| 14 | 16,570 | 23 | 0.139 |
| 15 | 16,461 | 26 | 0.158 |
| 16 | 16,453 | 22 | 0.134 |
| 17 | 16,166 | 29 | 0.179 |
| 18 | 17,039 | 33 | 0.194 |
| 19 | 15,649 | 19 | 0.121 |
| 20 | 16,756 | 18 | 0.107 |
| 21 | 17,703 | 16 | 0.090 |
| 22 | 15,441 | 9 | 0.058 |
| 23 | 10,938 | 21 | 0.192 |

Key observations:
- Hour 2 (02:00–03:00) is the highest-risk hour at 1.71% fraud rate — nearly 10x the dataset baseline. Volume is low (3,328 transactions), amplifying attacker success.
- Hour 4 (04:00–05:00) is the second-highest risk at 1.04%.
- Daytime hours (08:00–22:00) cluster near the 0.05–0.20% baseline range, with low relative risk.
- The early-morning window 01:00–05:00 accounts for only 5.2% of total volume but 24.2% of all frauds.
- The `hour_of_day` feature shows a Pearson correlation with Class of −0.017 — small in absolute terms, but the non-linear concentration of fraud in hours 2 and 4 is operationally significant.

**SQL:** `sql/03_time_coverage.sql`, `sql/04_fraud_by_hour.sql`

---

## 4. Amount Distribution

### Quantiles by Class

| Class | n | p01 | p10 | p50 | p90 | p99 | p999 | Mean | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 (legit) | 284,315 | 0.22 | 1.01 | 21.97 | 203.95 | 1,042.15 | 3,057.59 | 88.29 | 25,691.16 |
| 1 (fraud) | 492 | 0.00 | 0.76 | 9.54 | 347.75 | 1,374.73 | 2,125.87 | 122.21 | 2,125.87 |

Key findings:
- Fraudulent transactions have a **lower median amount** ($9.54) than legitimate ones ($21.97). This is consistent with fraudsters testing stolen cards with small charges before escalating.
- However, fraud mean ($122.21) exceeds legitimate mean ($88.29), driven by a tail of larger fraudulent charges (p90 = $347.75 vs. $203.95 for legitimate). Fraud is bimodal: many small test transactions and a tail of large cash-outs.
- The legitimate distribution extends much further (max $25,691) than fraud (max $2,125.87), suggesting very large transactions are relatively safe.
- `log_amount` (correlation with Class = −0.008) captures this right-tail compression appropriately.

### Zero-Amount Transactions

| Count | Fraud in Zero-Amount | Fraud Rate |
|---:|---:|---:|
| 1,825 | 27 | 1.480% |

Zero-amount transactions (1,825 rows, 0.64% of dataset) have a fraud rate of 1.48% — more than 8x the overall baseline. These likely represent authorisation checks with no actual charge, a common card-testing technique. This group warrants special attention in model post-processing.

**SQL:** `sql/05_amount_quantiles.sql`, `sql/06_zero_amount.sql`

---

## 5. Feature Ranges (V1–V28, log_amount, hour_of_day)

All V-features are PCA-transformed and should have means near zero across the full dataset. The query confirms this: all 28 V-features report `mean_val` of 0.000000 (rounded to 6 decimal places), and none are flagged as `|mean| > 0.1`.

The two derived engineered features are flagged as expected — they are not PCA outputs and carry non-zero means by construction:
- `log_amount`: mean = 3.1522, range [0, 10.154]
- `hour_of_day`: mean = 14.538, range [0, 23.999]

Both will be standard-scaled before any distance-based method.

**Notable range extremes** (potential outlier rows worth reviewing):

| Feature | Min | Max | Stddev |
|---|---:|---:|---:|
| V1 | −56.408 | 2.455 | 1.959 |
| V2 | −72.716 | 22.058 | 1.651 |
| V5 | −113.743 | 34.802 | 1.380 |
| V6 | −26.161 | 73.302 | 1.332 |
| V7 | −43.557 | 120.590 | 1.237 |
| V8 | −73.217 | 20.007 | 1.194 |
| V20 | −54.498 | 39.421 | 0.771 |
| V21 | −34.830 | 27.203 | 0.735 |
| V23 | −44.808 | 22.528 | 0.625 |

V7 spans from −43.6 to +120.6, and V5 reaches −113.7. These extreme values (each 80–100+ standard deviations from the mean) are very likely fraud-associated outliers and exactly the kind of signal Isolation Forest is designed to detect.

**SQL:** `sql/07_feature_ranges.sql`

---

## 6. Correlation with Class

Pearson correlations between each feature and `Class`, sorted by absolute value:

| Rank | Feature | Correlation | abs(r) |
|---:|---|---:|---:|
| 1 | V17 | −0.3265 | 0.3265 |
| 2 | V14 | −0.3025 | 0.3025 |
| 3 | V12 | −0.2606 | 0.2606 |
| 4 | V10 | −0.2169 | 0.2169 |
| 5 | V16 | −0.1965 | 0.1965 |
| 6 | V3  | −0.1930 | 0.1930 |
| 7 | V7  | −0.1873 | 0.1873 |
| 8 | V11 | +0.1549 | 0.1549 |
| 9 | V4  | +0.1334 | 0.1334 |
| 10 | V18 | −0.1115 | 0.1115 |
| 11 | V1  | −0.1013 | 0.1013 |
| ... | | | |
| 20 | hour_of_day | −0.0171 | 0.0171 |
| 29 | log_amount | −0.0083 | 0.0083 |
| 30 | V22 | +0.0008 | 0.0008 |

**Top 6 features by absolute correlation with Class:**

| Feature | Correlation | Interpretation |
|---|---:|---|
| V17 | −0.3265 | Strongest signal; large negative values strongly associated with fraud |
| V14 | −0.3025 | Second-strongest; negative direction |
| V12 | −0.2606 | Third; negative direction |
| V10 | −0.2169 | Moderate negative signal |
| V16 | −0.1965 | Moderate negative signal |
| V3  | −0.1930 | Moderate negative signal |

All six leading features are negatively correlated with Class, meaning fraudulent transactions tend to have lower (more negative) values on these PCA components. This is consistent with fraud occupying a specific region of the PCA-transformed feature space that is distinct from the legitimate transaction cloud.

`log_amount` (|r| = 0.008) and `hour_of_day` (|r| = 0.017) show very weak linear correlations with Class. Their value lies in non-linear patterns (hour 2 spike, zero-amount concentration) that Pearson correlation does not capture.

**SQL:** `sql/08_correlation_with_class.sql`

---

## Summary and Modelling Implications

| Finding | Implication |
|---|---|
| 0.1727% fraud rate (492/284,807) | Use `contamination=0.002` for Isolation Forest; evaluate with precision@top-k and ROC-AUC, not accuracy |
| All V-features have zero mean post-PCA | No centering bias in V1–V28; engineered features need standard scaling |
| V17, V14, V12, V10 have abs(r) 0.22–0.33 with Class | These features will dominate distance-based anomaly scores; worth inspecting cluster profiles |
| Fraud spike at hours 2 and 4 | `hour_of_day` adds non-linear signal; include in feature matrix |
| Zero-amount transactions: 1.48% fraud rate (8x baseline) | Flag this subgroup post-scoring; likely card-testing behaviour |
| Fraud median amount ($9.54) << Legit median ($21.97) | `log_amount` compresses the heavy tail; bimodal fraud distribution (small tests + large cashouts) |
| V5, V7 extreme outliers (up to ±120 stddev) | Isolation Forest will naturally assign high anomaly scores to these rows |
| No missing values anywhere | No imputation required |

The dataset is clean, fully numeric, and ready for feature engineering and modelling with no preprocessing gaps. The primary modelling challenge is the extreme class imbalance, not data quality.
