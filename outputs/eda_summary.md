# EDA Summary — Credit Card Fraud Detection

**Run ID:** 2026-04-26_1822
**Dataset:** `data/creditcard.csv`
**Profiled with:** DuckDB (in-process), Python 3.10+
**Analysis date:** 2026-04-26

---

## 1. Schema and Shape

| Attribute | Value |
|-----------|-------|
| Rows | 284,807 |
| Columns | 31 |
| Disk size | 98.2 MB (102,919,038 bytes) |
| Time span | 0 – 172,792 seconds (48.00 hours) |
| Fraud rows | 492 (0.1727 %) |
| Legit rows | 284,315 (99.8273 %) |
| Null values | None detected in any column |

**Column inventory:**

| Column | Type | Notes |
|--------|------|-------|
| `Time` | BIGINT | Seconds elapsed from first transaction |
| `V1` – `V28` | DOUBLE | Anonymized PCA-transformed features |
| `Amount` | DOUBLE | Transaction amount in USD |
| `Class` | BIGINT | 0 = legitimate, 1 = fraud (eval-only) |

The dataset covers exactly two calendar days of European cardholder transactions.
`Time` and `Class` are 64-bit integers; all 28 PCA components and `Amount` are
64-bit floats. No null values were found in any column, so no imputation step is
needed in the ML pipeline.

---

## 2. Class Balance

| Class | Label | Count | Percentage |
|-------|-------|------:|----------:|
| 0 | Legitimate | 284,315 | 99.8273 % |
| 1 | Fraud | 492 | 0.1727 % |

The positive-class (fraud) prevalence is **0.1727 %** — fewer than 2 fraud
transactions per 1,000. Raw accuracy would read 99.83 % even for a classifier
that never predicts fraud, making it a meaningless metric. The appropriate
evaluation metrics are ROC-AUC, precision-at-top-k, and recall-at-top-k.

For Isolation Forest the contamination hyperparameter will be set to **0.002**
(0.2 %), slightly above the true rate, to avoid missing borderline cases.

---

## 3. Time Coverage

- **min(Time):** 0 seconds
- **max(Time):** 172,792 seconds
- **Span:** exactly 48.00 hours (2 calendar days)

### Feature engineering from Time

| Feature | Formula | Range |
|---------|---------|-------|
| `hour_of_day` | `(Time % 86400) / 3600.0` | [0.0, 23.999) |
| `day` | `FLOOR(Time / 86400)` cast int | {0, 1} |

Raw `Time` is dropped from the model feature matrix after these derivations.

### Fraud rate by hour of day

| Hour | Transactions | Fraud | Fraud Rate |
|-----:|-------------:|------:|-----------:|
| 0 | 7,695 | 6 | 0.078 % |
| 1 | 4,220 | 10 | 0.237 % |
| **2** | **3,328** | **57** | **1.713 %** |
| 3 | 3,492 | 17 | 0.487 % |
| 4 | 2,209 | 23 | 1.041 % |
| 5 | 2,990 | 11 | 0.368 % |
| 6 | 4,101 | 9 | 0.220 % |
| 7 | 7,243 | 23 | 0.318 % |
| 8 | 10,276 | 9 | 0.088 % |
| 9 | 15,838 | 16 | 0.101 % |
| 10 | 16,598 | 8 | 0.048 % |
| **11** | **16,856** | **53** | **0.314 %** |
| 12 | 15,420 | 17 | 0.110 % |
| 13 | 15,365 | 17 | 0.111 % |
| 14 | 16,570 | 23 | 0.139 % |
| 15 | 16,461 | 26 | 0.158 % |
| 16 | 16,453 | 22 | 0.134 % |
| 17 | 16,166 | 29 | 0.179 % |
| 18 | 17,039 | 33 | 0.194 % |
| 19 | 15,649 | 19 | 0.121 % |
| 20 | 16,756 | 18 | 0.107 % |
| 21 | 17,703 | 16 | 0.090 % |
| 22 | 15,441 | 9 | 0.058 % |
| 23 | 10,938 | 21 | 0.192 % |

**Peak fraud hour: 2 AM at 1.713 %** — roughly 10x the daytime baseline.
Hours 2–4 AM together account for elevated risk; hour 11 AM also shows a
secondary spike (0.314 %). The early-morning pattern (low transaction volume,
higher attacker activity) is a well-known card-fraud temporal signature.

Transaction volume follows the expected daily rhythm: low overnight (hours 0–7,
roughly 2,200–7,700 txns/hr) and high during business hours (hours 8–22,
roughly 10,000–17,700 txns/hr). This means the absolute fraud count is actually
largest during daytime hours even though the rate is lower.

---

## 4. Amount Distribution

### Quantiles by class

| Quantile | Legitimate | Fraud |
|----------|----------:|------:|
| Min | $0.00 | $0.00 |
| p01 | $0.21 | $0.00 |
| p10 | $1.01 | $0.76 |
| **p50 (median)** | **$22.03** | **$9.54** |
| p90 | $204.43 | $347.75 |
| p99 | $1,028.33 | $1,374.73 |
| p99.9 | $3,037.16 | $2,125.87 |
| Mean | $88.29 | $122.21 |
| Std dev | $250.12 | $256.68 |
| Max | $25,691.16 | $2,125.87 |

Fraudulent transactions display a **bimodal amount signature**:

- The **median is much lower** than legitimate ($9.54 vs $22.03), indicating
  a large cluster of small test charges used to verify card validity.
- The **mean is higher** ($122.21 vs $88.29), driven by a tail of larger
  fraudulent purchases in the $300–$2,000 range.
- The **maximum fraud amount** ($2,125.87) is far below the maximum legitimate
  amount ($25,691.16), confirming that very large transactions are rarely
  fraudulent in this dataset.

The heavy right tail in both classes confirms that `log_amount = log1p(Amount)`
is the correct transformation before applying distance-based ML methods.

### Zero-amount transactions

| Metric | Value |
|--------|------:|
| Total zero-amount transactions | 1,825 |
| Fraud among them | 27 |
| Fraud rate | 1.480 % |
| As % of all fraud | 5.49 % |

1,825 transactions (0.64 % of the dataset) have `Amount = 0`. Their fraud rate
of **1.48 % is 8.6x the overall baseline** (0.173 %), making zero-amount a
weak but actionable signal. These are likely authorization-only probes used by
fraudsters to confirm a stolen card is active before executing larger charges.

---

## 5. Feature Ranges (V1–V28 and Derived Features)

### PCA components V1–V28

All 28 PCA components have means indistinguishable from zero (largest absolute
mean observed: < 0.000001 after rounding to 6 decimal places). This is expected
given the PCA centering applied upstream by the dataset creators. **None of
V1–V28 triggered the |mean| > 0.1 flag.**

Selected statistics for V-features (extremes highlighted):

| Feature | Min | Max | Mean | Std Dev |
|---------|----:|----:|-----:|--------:|
| V1 | -56.41 | 2.45 | ~0 | 1.96 |
| V2 | -72.72 | 22.06 | ~0 | 1.65 |
| V3 | -48.33 | 9.38 | ~0 | 1.52 |
| V4 | -5.68 | 16.88 | ~0 | 1.42 |
| V5 | -113.74 | 34.80 | ~0 | 1.38 |
| V6 | -26.16 | 73.30 | ~0 | 1.33 |
| V7 | -43.56 | 120.59 | ~0 | 1.24 |
| V8 | -73.22 | 20.01 | ~0 | 1.19 |
| V9 | -13.43 | 15.59 | ~0 | 1.10 |
| V10 | -24.59 | 23.75 | ~0 | 1.09 |
| V11 | -4.80 | 12.02 | ~0 | 1.02 |
| V12 | -18.68 | 7.85 | ~0 | 1.00 |
| V13 | -5.79 | 7.13 | ~0 | 1.00 |
| V14 | -19.21 | 10.53 | ~0 | 0.96 |
| V15 | -4.50 | 8.88 | ~0 | 0.92 |
| V16 | -14.13 | 17.32 | ~0 | 0.88 |
| V17 | -25.16 | 9.25 | ~0 | 0.85 |
| V18 | -9.50 | 5.04 | ~0 | 0.84 |
| V19 | -7.21 | 5.59 | ~0 | 0.81 |
| V20 | -54.50 | 39.42 | ~0 | 0.77 |
| V21 | -34.83 | 27.20 | ~0 | 0.73 |
| V22 | -10.93 | 10.50 | ~0 | 0.73 |
| V23 | -44.81 | 22.53 | ~0 | 0.62 |
| V24 | -2.84 | 4.58 | ~0 | 0.61 |
| V25 | -10.30 | 7.52 | ~0 | 0.52 |
| V26 | -2.60 | 3.52 | ~0 | 0.48 |
| V27 | -22.57 | 31.61 | ~0 | 0.40 |
| V28 | -15.43 | 33.85 | ~0 | 0.33 |

V5 (-113.74 to 34.80) and V7 (-43.56 to 120.59) have the widest absolute ranges,
indicating occasional extreme transactions captured on those PCA axes. Standard
deviations decrease roughly monotonically from V1 to V28, consistent with PCA
ordering by explained variance.

### Derived features (flagged by |mean| > 0.1)

| Feature | Mean | Std Dev | Flag | Interpretation |
|---------|-----:|--------:|------|----------------|
| `hour_of_day` | 14.54 | 5.85 | FLAG | Expected — real-world time value |
| `log_amount` | 3.15 | 1.66 | FLAG | Expected — log1p of USD amounts |

Both flags are expected and harmless. These features represent real-world
measurements that are not PCA-centered. `StandardScaler` will normalize them
before distance-based modelling.

---

## 6. Correlation with Class

Pearson correlations between each feature and the binary `Class` label, sorted
by absolute value:

| Rank | Feature | Correlation | Abs Corr |
|-----:|---------|------------:|---------:|
| 1 | V17 | -0.3265 | 0.3265 |
| 2 | V14 | -0.3025 | 0.3025 |
| 3 | V12 | -0.2606 | 0.2606 |
| 4 | V10 | -0.2169 | 0.2169 |
| 5 | V16 | -0.1965 | 0.1965 |
| 6 | V3 | -0.1930 | 0.1930 |
| 7 | V7 | -0.1873 | 0.1873 |
| 8 | V11 | +0.1549 | 0.1549 |
| 9 | V4 | +0.1334 | 0.1334 |
| 10 | V18 | -0.1115 | 0.1115 |
| 11 | V1 | -0.1013 | 0.1013 |
| ... | ... | ... | ... |
| 28 | V22 | +0.0008 | 0.0008 |

Full rankings saved to `outputs/eda/08_correlations.parquet`.

All top-6 correlators are **negatively** correlated with fraud — fraud
transactions tend to have significantly lower (more negative) values on these
PCA axes. V11 and V4 are notable exceptions, being positively correlated:
fraud transactions have higher values on these dimensions.

Pearson correlation is a linear measure and is sensitive to class imbalance
(492 fraud vs 284,315 legit). The rankings nonetheless agree strongly with
the mean-difference analysis, providing cross-method validation.

`log_amount` (corr = -0.0083) and `hour_of_day` (corr = -0.0171) have very
weak linear correlations with Class, confirming they are supplementary rather
than primary signals in the feature matrix.

---

## 7. Key Observations for the ML Stage

1. **Severe class imbalance (0.173 %)** requires contamination = 0.002 for
   Isolation Forest. Precision-at-top-k and ROC-AUC are the mandatory
   evaluation metrics; raw accuracy is meaningless.

2. **V17 and V14 are the strongest linear separators** (|corr| = 0.327 and
   0.303 respectively). Both are negatively correlated — fraud has lower values.
   Any anomaly model should be especially sensitive to these axes.

3. **Six features drive most linear separation:** V17, V14, V12, V10, V16, V3.
   These are the primary anchors to inspect in cluster profiles and anomaly score
   breakdowns.

4. **Amount bimodality is a useful secondary signal:** fraud median ($9.54) is
   less than half the legitimate median ($22.03), and zero-amount transactions
   carry an 8.6x fraud-rate uplift. Use `log_amount`; drop raw `Amount`.

5. **Temporal signal exists but is limited:** the 2 AM spike (1.71 % fraud rate)
   is noteworthy, but `hour_of_day` has a correlation of only -0.017 with Class.
   Include it as a feature but treat it as supplementary.

6. **All V-features have effectively zero mean post-PCA** — no re-centering is
   needed. `StandardScaler` is still required to equalize the variance differences
   across features (V1 std ~1.96 vs V28 std ~0.33) before LOF and One-Class SVM.

7. **No missing values** — no imputation step is required anywhere in the
   pipeline.

8. **Very large legitimate transactions (> $10,000) have no fraud counterpart**
   in this dataset — consider capping or noting this in model documentation.

---

## SQL Files Produced

| File | Purpose |
|------|---------|
| `sql/01_schema_shape.sql` | DESCRIBE — column names and types via DuckDB |
| `sql/02_class_balance.sql` | Class counts and percentages |
| `sql/03_time_coverage.sql` | min/max Time and span in hours |
| `sql/04_fraud_by_hour.sql` | Fraud rate by integer hour_of_day |
| `sql/05_amount_quantiles.sql` | Amount quantiles at 6 levels by class |
| `sql/06_zero_amount.sql` | Count and fraud rate of Amount = 0 rows |
| `sql/07_feature_ranges.sql` | Min/max/mean/std for V1–V28 and derived features |
| `sql/08_correlation_with_class.sql` | Pearson corr of all features vs Class |

## Intermediate Parquet Outputs

All intermediate results saved under `outputs/eda/`:

| File | Content |
|------|---------|
| `02_class_balance.parquet` | Class counts and percentages |
| `03_time_coverage.parquet` | Time min, max, span |
| `04_fraud_by_hour.parquet` | 24-row hourly fraud rate table |
| `05_amount_quantiles.parquet` | Amount quantile distribution by class |
| `06_zero_amount.parquet` | Zero-amount transaction stats |
| `07_feature_ranges.parquet` | Feature range and flag table |
| `08_correlations.parquet` | Full feature-class correlation ranking |

---

*Generated by `sql/run_eda_full.py` on 2026-04-26 (Run ID: 2026-04-26_1822)*
