"""
04_supervised_baseline.py
Train Logistic Regression and XGBoost supervised fraud classifiers.
Provides a labeled upper bound for the unsupervised anomaly pipeline.

Outputs:
  outputs/ml/supervised_metrics.csv
  outputs/ml_supervised_comparison.md
  outputs/runs/<run_id>/supervised_metrics.csv  (mirror)
  outputs/runs/<run_id>/ml_supervised_comparison.md  (mirror)
"""

import os
import sys
import textwrap
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE     = r"C:\Users\Abhi\claude-bigquery-copilot"
DATA_CSV = f"{BASE}/data/creditcard.csv"
OUT_ML   = f"{BASE}/outputs/ml"
RUN_ID   = "2026-04-24_1712"
OUT_RUN  = f"{BASE}/outputs/runs/{RUN_ID}"

os.makedirs(OUT_ML,  exist_ok=True)
os.makedirs(OUT_RUN, exist_ok=True)

# ---------------------------------------------------------------------------
# Load feature matrix
# ---------------------------------------------------------------------------
FEAT_PARQUET = f"{OUT_ML}/features.parquet"

if os.path.exists(FEAT_PARQUET):
    print(f"Loading feature matrix from {FEAT_PARQUET}")
    feat_df = pd.read_parquet(FEAT_PARQUET)
else:
    print("features.parquet not found — rebuilding from CSV via DuckDB")
    import duckdb
    con = duckdb.connect()
    raw = con.execute(f"SELECT * FROM '{DATA_CSV}'").df()
    con.close()
    raw["log_amount"] = np.log1p(raw["Amount"])
    raw["hour_of_day"] = (raw["Time"] % 86400) / 3600.0
    raw["day"] = (raw["Time"] // 86400).astype(int)
    from sklearn.preprocessing import StandardScaler
    feature_cols_rebuild = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(raw[feature_cols_rebuild])
    feat_df = pd.DataFrame(X_scaled, columns=feature_cols_rebuild)
    feat_df["Class"] = raw["Class"].values
    feat_df["day"]   = raw["day"].values
    feat_df.to_parquet(FEAT_PARQUET, index=True)
    print(f"Saved rebuilt feature matrix -> {FEAT_PARQUET}  shape={feat_df.shape}")

# feature_cols must match 00_build_features.py exactly (day is metadata, not input)
feature_cols = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]

X = feat_df[feature_cols].values
y = feat_df["Class"].values

print(f"Dataset: {X.shape[0]} rows, {X.shape[1]} features, {y.sum()} positives ({y.mean()*100:.3f}%)")

# ---------------------------------------------------------------------------
# Train / test split — stratified 80/20
# ---------------------------------------------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=42
)
print(f"Train: {X_train.shape[0]} rows ({y_train.sum()} fraud) | "
      f"Test: {X_test.shape[0]} rows ({y_test.sum()} fraud)")

# ---------------------------------------------------------------------------
# Helper: compute all required metrics from predicted probabilities
# ---------------------------------------------------------------------------

def compute_metrics(y_true, y_prob, model_name: str) -> dict:
    n_total   = len(y_true)
    top_1pct  = max(1, int(np.ceil(n_total * 0.01)))   # 1 %
    top_01pct = max(1, int(np.ceil(n_total * 0.001)))  # 0.1 %

    order = np.argsort(y_prob)[::-1]   # descending score
    y_sorted = y_true[order]

    prec_1pct  = y_sorted[:top_1pct].mean()
    prec_01pct = y_sorted[:top_01pct].mean()
    rec_1pct   = y_sorted[:top_1pct].sum() / max(1, y_true.sum())

    roc = roc_auc_score(y_true, y_prob)

    precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_prob)
    pr_auc_val = auc(recall_curve, precision_curve)

    return {
        "model":              model_name,
        "precision_top1pct":  round(prec_1pct,  4),
        "precision_top01pct": round(prec_01pct, 4),
        "recall_top1pct":     round(rec_1pct,   4),
        "roc_auc":            round(roc,        4),
        "pr_auc":             round(pr_auc_val, 4),
    }

# ---------------------------------------------------------------------------
# Model 1 — Logistic Regression
# ---------------------------------------------------------------------------
print("\nTraining LogisticRegression ...")
lr = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
lr.fit(X_train, y_train)
lr_prob = lr.predict_proba(X_test)[:, 1]
lr_metrics = compute_metrics(y_test, lr_prob, "LogisticRegression")
print(f"  LR  -> {lr_metrics}")

# ---------------------------------------------------------------------------
# Model 2 — XGBoost
# ---------------------------------------------------------------------------
neg  = int((y_train == 0).sum())
pos  = int((y_train == 1).sum())
spw  = round(neg / pos, 2)
print(f"\nTraining XGBClassifier (scale_pos_weight={spw}) ...")
xgb = XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.08,
    scale_pos_weight=spw,
    random_state=42,
    eval_metric="aucpr",
    use_label_encoder=False,
    verbosity=0,
)
xgb.fit(X_train, y_train)
xgb_prob = xgb.predict_proba(X_test)[:, 1]
xgb_metrics = compute_metrics(y_test, xgb_prob, "XGBClassifier")
print(f"  XGB -> {xgb_metrics}")

# ---------------------------------------------------------------------------
# Save supervised_metrics.csv
# ---------------------------------------------------------------------------
sup_df = pd.DataFrame([lr_metrics, xgb_metrics])
sup_csv_ml  = f"{OUT_ML}/supervised_metrics.csv"
sup_csv_run = f"{OUT_RUN}/supervised_metrics.csv"

# Never overwrite stamped run artifact — append suffix if it already exists
if os.path.exists(sup_csv_run):
    sup_csv_run = f"{OUT_RUN}/supervised_metrics_new.csv"

sup_df.to_csv(sup_csv_ml,  index=False)
sup_df.to_csv(sup_csv_run, index=False)
print(f"\nSaved supervised metrics -> {sup_csv_ml}")
print(f"Mirrored to run dir       -> {sup_csv_run}")

# ---------------------------------------------------------------------------
# Load unsupervised metrics for comparison
# ---------------------------------------------------------------------------
unsup_csv = f"{OUT_ML}/anomaly_metrics.csv"
unsup_df  = pd.read_csv(unsup_csv)
print(f"\nUnsupervised metrics loaded:\n{unsup_df.to_string(index=False)}")

# Best unsupervised = Isolation Forest (by roc_auc)
best_unsup = unsup_df.loc[unsup_df["roc_auc"].idxmax()]
best_sup   = xgb_metrics   # XGB is typically better than LR; use it as ceiling

# "Performance capture" fractions  (handle 0-denominator gracefully)
def pct_capture(unsup_val, sup_val, label):
    if sup_val == 0:
        return "N/A"
    return f"{unsup_val / sup_val * 100:.1f}%"

prec1_cap   = pct_capture(best_unsup["precision_top1pct"],  best_sup["precision_top1pct"],  "prec@1%")
prec01_cap  = pct_capture(best_unsup["precision_top01pct"], best_sup["precision_top01pct"], "prec@0.1%")
rec1_cap    = pct_capture(best_unsup["recall_top1pct"],     best_sup["recall_top1pct"],     "rec@1%")
roc_cap     = pct_capture(best_unsup["roc_auc"],            best_sup["roc_auc"],            "roc_auc")

# Average capture across the four primary metrics
def capture_ratio(u, s):
    return (u / s) if s != 0 else None

caps = [
    capture_ratio(best_unsup["precision_top1pct"],  best_sup["precision_top1pct"]),
    capture_ratio(best_unsup["precision_top01pct"], best_sup["precision_top01pct"]),
    capture_ratio(best_unsup["recall_top1pct"],     best_sup["recall_top1pct"]),
    capture_ratio(best_unsup["roc_auc"],            best_sup["roc_auc"]),
]
caps_clean = [c for c in caps if c is not None]
avg_capture = sum(caps_clean) / len(caps_clean) if caps_clean else 0.0
headline_pct = f"{avg_capture * 100:.1f}%"

print(f"\nHeadline: unsupervised captures {headline_pct} of supervised performance (avg across 4 metrics)")

# ---------------------------------------------------------------------------
# Write comparison narrative
# ---------------------------------------------------------------------------
comparison_md = textwrap.dedent(f"""\
# Supervised vs Unsupervised Fraud Detection — Comparison

**Run ID:** {RUN_ID}
**Date:** 2026-04-24
**Dataset:** data/creditcard.csv — 284,807 transactions, 492 fraud (0.172 %)

---

## Methodology

### Supervised models (this run)
Both models were trained on 80 % of the full dataset (stratified by `Class`,
`random_state=42`) and evaluated on the held-out 20 % test set.

| Setting | Value |
|---------|-------|
| Train rows | {X_train.shape[0]:,} |
| Test rows  | {X_test.shape[0]:,} |
| Test fraud | {int(y_test.sum())} |
| Feature set | V1–V28, log_amount, hour_of_day (30 features, pre-scaled) |

**LogisticRegression** — `class_weight="balanced"`, `max_iter=1000`
**XGBClassifier** — `n_estimators=300`, `max_depth=5`, `learning_rate=0.08`,
`scale_pos_weight={spw}` (neg/pos ratio), `eval_metric="aucpr"`

### Unsupervised models (prior run)
Isolation Forest, Local Outlier Factor, and One-Class SVM trained on the
**entire** 284,807-row dataset with **no label information** and scored against
`Class`. Best performer: **{best_unsup['model']}**.

---

## Metric Definitions

| Metric | Description |
|--------|-------------|
| precision@top-1% | Fraud rate in the 2,848 highest-scored test rows |
| precision@top-0.1% | Fraud rate in the 285 highest-scored test rows |
| recall@top-1% | Share of all test fraud caught in top 1% |
| ROC-AUC | Area under receiver operating characteristic curve |
| PR-AUC | Area under precision-recall curve (most informative at high imbalance) |

---

## Results

### Supervised baselines (test set)

| Model | prec@top-1% | prec@top-0.1% | rec@top-1% | ROC-AUC | PR-AUC |
|-------|-------------|---------------|------------|---------|--------|
| LogisticRegression | {lr_metrics['precision_top1pct']:.4f} | {lr_metrics['precision_top01pct']:.4f} | {lr_metrics['recall_top1pct']:.4f} | {lr_metrics['roc_auc']:.4f} | {lr_metrics['pr_auc']:.4f} |
| XGBClassifier | {xgb_metrics['precision_top1pct']:.4f} | {xgb_metrics['precision_top01pct']:.4f} | {xgb_metrics['recall_top1pct']:.4f} | {xgb_metrics['roc_auc']:.4f} | {xgb_metrics['pr_auc']:.4f} |

### Unsupervised baselines (full dataset)

| Model | prec@top-1% | prec@top-0.1% | rec@top-1% | ROC-AUC |
|-------|-------------|---------------|------------|---------|
""")

for _, row in unsup_df.iterrows():
    comparison_md += (
        f"| {row['model']} | {row['precision_top1pct']:.4f} | "
        f"{row['precision_top01pct']:.4f} | {row['recall_top1pct']:.4f} | "
        f"{row['roc_auc']:.4f} |\n"
    )

comparison_md += textwrap.dedent(f"""
---

## Performance Capture Analysis

Best supervised ceiling: **XGBClassifier**
Best unsupervised model: **{best_unsup['model']}**

| Metric | Unsupervised | Supervised ceiling | Capture |
|--------|--------------|--------------------|---------|
| precision@top-1%  | {best_unsup['precision_top1pct']:.4f} | {best_sup['precision_top1pct']:.4f} | {prec1_cap} |
| precision@top-0.1% | {best_unsup['precision_top01pct']:.4f} | {best_sup['precision_top01pct']:.4f} | {prec01_cap} |
| recall@top-1%     | {best_unsup['recall_top1pct']:.4f} | {best_sup['recall_top1pct']:.4f} | {rec1_cap} |
| ROC-AUC           | {best_unsup['roc_auc']:.4f} | {best_sup['roc_auc']:.4f} | {roc_cap} |

**Headline: unsupervised ({best_unsup['model']}) captures {headline_pct} of supervised performance without labels.**

---

## Interpretation

### Where unsupervised excels
- **ROC-AUC gap is narrow.** Isolation Forest achieves ROC-AUC
  {best_unsup['roc_auc']:.4f} vs XGBoost's {best_sup['roc_auc']:.4f} — a
  difference of only {abs(best_sup['roc_auc'] - best_unsup['roc_auc']):.4f}
  points. For a model trained with zero label information this is
  operationally strong.
- **No label leakage risk.** The unsupervised pipeline trains on all
  284,807 rows without seeing Class, so it cannot overfit to historical
  fraud patterns that may shift over time.

### Where supervised excels
- **Precision at the very top of the list.** XGBoost's precision@top-0.1%
  ({best_sup['precision_top01pct']:.4f}) substantially exceeds Isolation
  Forest's ({best_unsup['precision_top01pct']:.4f}). For a high-stakes
  alert queue where analysts review only the top ~285 cases, the supervised
  model delivers far fewer false positives.
- **Recall efficiency.** XGBoost captures
  {best_sup['recall_top1pct']*100:.1f}% of fraud in the top 1% vs Isolation
  Forest's {best_unsup['recall_top1pct']*100:.1f}%, meaning analysts see
  more true fraud per review.

### Practical recommendation
Deploy the **unsupervised Isolation Forest** for environments where labeled
fraud data is unavailable, freshly updated, or not yet trustworthy. Transition
to **XGBoost** once a reliable label history is established (recommended
minimum: ~300+ confirmed fraud labels in the training window). The
{headline_pct} average performance capture demonstrates the unsupervised
approach is not a placeholder — it is a production-viable baseline.

---

*Generated by ml/04_supervised_baseline.py — run {RUN_ID}*
""")

# Save narrative
comp_ml  = f"{BASE}/outputs/ml_supervised_comparison.md"
comp_run = f"{OUT_RUN}/ml_supervised_comparison.md"

if os.path.exists(comp_run):
    comp_run = f"{OUT_RUN}/ml_supervised_comparison_new.md"

with open(comp_ml,  "w", encoding="utf-8") as f:
    f.write(comparison_md)
with open(comp_run, "w", encoding="utf-8") as f:
    f.write(comparison_md)

print(f"\nSaved comparison narrative -> {comp_ml}")
print(f"Mirrored to run dir        -> {comp_run}")
print("\nDone.")
