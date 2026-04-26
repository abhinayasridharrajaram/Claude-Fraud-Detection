"""
01_anomaly_detection.py
Anomaly detection: Isolation Forest, Local Outlier Factor, One-Class SVM.
Outputs:
  outputs/ml/anomaly_scores.parquet
  outputs/ml/anomaly_metrics.csv
  outputs/ml/anomaly_pr_curves.png
"""

import sys
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.preprocessing import StandardScaler

# -- paths ----------------------------------------------------------------------
BASE    = r"C:\Users\Abhi\claude-bigquery-copilot"
OUT_DIR = f"{BASE}/outputs/ml"
os.makedirs(OUT_DIR, exist_ok=True)

# -- load features --------------------------------------------------------------
print("Loading feature matrix ?")
feat_df = pd.read_parquet(f"{OUT_DIR}/features.parquet")

EXPECTED_ROWS = 284_807
if len(feat_df) != EXPECTED_ROWS:
    sys.exit(f"ERROR: expected {EXPECTED_ROWS} rows, got {len(feat_df)}")
print(f"Row count verified: {len(feat_df)}")

feature_cols = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]
X     = feat_df[feature_cols].values
y     = feat_df["Class"].values          # held-out labels ? eval only
n     = len(X)

# -- helper: convert sklearn decision scores to "higher = more anomalous" ------?
def invert_if_needed(scores):
    """sklearn anomaly models return lower scores for anomalies; negate so
    higher score -> more anomalous (consistent with ranking logic)."""
    return -scores

# ----------------------------------------------------------------------------?
# 1. Isolation Forest
# ----------------------------------------------------------------------------?
print("\nFitting Isolation Forest ?")
iforest = IsolationForest(n_estimators=200, contamination=0.002,
                          random_state=42, n_jobs=-1)
iforest.fit(X)
if_raw    = iforest.score_samples(X)   # lower = more anomalous
if_score  = invert_if_needed(if_raw)   # higher = more anomalous
print(f"  IF score range: [{if_score.min():.4f}, {if_score.max():.4f}]")

# ----------------------------------------------------------------------------?
# 2. Local Outlier Factor  (novelty=False ? transductive)
# ----------------------------------------------------------------------------?
print("Fitting Local Outlier Factor (this may take a few minutes) ?")
lof = LocalOutlierFactor(n_neighbors=20, novelty=False,
                         contamination=0.002, n_jobs=-1)
lof.fit(X)
lof_raw   = lof.negative_outlier_factor_   # already on all 284 807 rows
lof_score = invert_if_needed(lof_raw)      # higher = more anomalous
print(f"  LOF score range: [{lof_score.min():.4f}, {lof_score.max():.4f}]")

# ----------------------------------------------------------------------------?
# 3. One-Class SVM on a stratified 20K subsample
# ----------------------------------------------------------------------------?
print("Fitting One-Class SVM on 20K stratified subsample ?")
rng = np.random.default_rng(42)

# Stratified subsample: preserve fraud ratio
fraud_idx  = np.where(y == 1)[0]
legit_idx  = np.where(y == 0)[0]

n_sub      = 20_000
n_fraud_sub = min(len(fraud_idx), int(n_sub * (len(fraud_idx) / n)))
n_legit_sub = n_sub - n_fraud_sub

sub_fraud = rng.choice(fraud_idx, size=n_fraud_sub, replace=False)
sub_legit = rng.choice(legit_idx, size=n_legit_sub, replace=False)
sub_idx   = np.concatenate([sub_fraud, sub_legit])
rng.shuffle(sub_idx)

X_sub = X[sub_idx]

ocsvm = OneClassSVM(nu=0.002, kernel="rbf", gamma="scale")
ocsvm.fit(X_sub)

# Score ALL 284 807 rows
ocsvm_raw   = ocsvm.score_samples(X)   # lower = more anomalous
ocsvm_score = invert_if_needed(ocsvm_raw)
print(f"  OCSVM score range: [{ocsvm_score.min():.4f}, {ocsvm_score.max():.4f}]")

# ----------------------------------------------------------------------------?
# 4. Save anomaly_scores.parquet
# ----------------------------------------------------------------------------?
scores_df = pd.DataFrame({
    "index":      np.arange(n),
    "if_score":   if_score,
    "lof_score":  lof_score,
    "ocsvm_score": ocsvm_score,
    "Class":      y,
})
scores_path = f"{OUT_DIR}/anomaly_scores.parquet"
scores_df.to_parquet(scores_path, index=False)
print(f"\nSaved anomaly scores -> {scores_path}")

# ----------------------------------------------------------------------------?
# 5. Metrics
# ----------------------------------------------------------------------------?
def compute_metrics(score_col, label_col, model_name):
    n_total    = len(score_col)
    k1pct      = int(np.ceil(n_total * 0.01))    # top 1 %
    k01pct     = int(np.ceil(n_total * 0.001))   # top 0.1 %
    sorted_idx = np.argsort(score_col)[::-1]      # descending

    top_1pct_labels  = label_col[sorted_idx[:k1pct]]
    top_01pct_labels = label_col[sorted_idx[:k01pct]]

    prec_1pct  = top_1pct_labels.mean()
    prec_01pct = top_01pct_labels.mean()
    recall_1pct = top_1pct_labels.sum() / max(label_col.sum(), 1)
    roc_auc    = roc_auc_score(label_col, score_col)

    print(f"\n{model_name}:")
    print(f"  precision@top-1%  = {prec_1pct:.4f}   (k={k1pct})")
    print(f"  precision@top-0.1%= {prec_01pct:.4f}   (k={k01pct})")
    print(f"  recall@top-1%     = {recall_1pct:.4f}")
    print(f"  ROC-AUC           = {roc_auc:.4f}")

    return {
        "model":             model_name,
        "precision_top1pct": round(prec_1pct,  4),
        "precision_top01pct":round(prec_01pct, 4),
        "recall_top1pct":    round(recall_1pct,4),
        "roc_auc":           round(roc_auc,    4),
    }

print("\n-- Metrics ----------------------------------------------------------")
rows = [
    compute_metrics(if_score,    y, "IsolationForest"),
    compute_metrics(lof_score,   y, "LocalOutlierFactor"),
    compute_metrics(ocsvm_score, y, "OneClassSVM"),
]
metrics_df = pd.DataFrame(rows)
metrics_path = f"{OUT_DIR}/anomaly_metrics.csv"
metrics_df.to_csv(metrics_path, index=False)
print(f"\nSaved metrics -> {metrics_path}")

# ----------------------------------------------------------------------------?
# 6. Precision-Recall curves
# ----------------------------------------------------------------------------?
fig, ax = plt.subplots(figsize=(8, 6))
models = [
    ("IsolationForest",    if_score,    "#e15759"),
    ("LocalOutlierFactor", lof_score,   "#4e79a7"),
    ("OneClassSVM",        ocsvm_score, "#59a14f"),
]
for name, scores, color in models:
    prec, rec, _ = precision_recall_curve(y, scores)
    ap = average_precision_score(y, scores)
    ax.plot(rec, prec, label=f"{name} (AP={ap:.3f})", color=color, lw=1.8)

baseline = y.mean()
ax.axhline(baseline, color="gray", linestyle="--", lw=1,
           label=f"Baseline (fraud rate {baseline:.4f})")
ax.set_xlabel("Recall", fontsize=12)
ax.set_ylabel("Precision", fontsize=12)
ax.set_title("Precision-Recall Curves ? Anomaly Detection", fontsize=13)
ax.legend(fontsize=10)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.05])
plt.tight_layout()
pr_path = f"{OUT_DIR}/anomaly_pr_curves.png"
fig.savefig(pr_path, dpi=150)
plt.close(fig)
print(f"Saved PR curves -> {pr_path}")

print("\nDone ? anomaly detection complete.")
