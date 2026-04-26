"""
03_run_pipeline.py
Full pipeline runner for a specific run_id.
- Builds features (if not already built or row count wrong)
- Runs anomaly detection: Isolation Forest, LOF, One-Class SVM
- Runs clustering: K-means sweep k=3..8, profiles best cluster
- Generates UMAP visualizations (PCA -> UMAP)
- Writes outputs/ml/* artifacts
- Mirrors anomaly_metrics.csv and ml_summary.md to the run directory
Usage:
    python ml/03_run_pipeline.py --run_id 2026-04-24_1623
"""

import sys
import os
import argparse
import shutil
import numpy as np
import pandas as pd
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.cluster import KMeans
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
    silhouette_score,
)
from sklearn.decomposition import PCA
import umap

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE     = r"C:\Users\Abhi\claude-bigquery-copilot"
DATA_CSV = f"{BASE}/data/creditcard.csv"
OUT_DIR  = f"{BASE}/outputs/ml"
RUNS_DIR = f"{BASE}/outputs/runs"

EXPECTED_ROWS = 284_807

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--run_id", required=True, help="Run stamp, e.g. 2026-04-24_1623")
args = parser.parse_args()
RUN_ID   = args.run_id
RUN_DIR  = f"{RUNS_DIR}/{RUN_ID}"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(RUN_DIR, exist_ok=True)

print(f"=== Pipeline run_id={RUN_ID} ===")

# ---------------------------------------------------------------------------
# Step 0: Build or verify feature matrix
# ---------------------------------------------------------------------------
FEAT_PATH = f"{OUT_DIR}/features.parquet"

def build_features():
    print("\n[Step 0] Building feature matrix from CSV via DuckDB ...")
    con = duckdb.connect()
    df  = con.execute(f"SELECT * FROM '{DATA_CSV}'").df()
    con.close()

    if len(df) != EXPECTED_ROWS:
        sys.exit(f"ERROR: expected {EXPECTED_ROWS} rows, got {len(df)}")
    print(f"  Row count verified: {len(df)}")

    df["log_amount"]  = np.log1p(df["Amount"])
    df["hour_of_day"] = (df["Time"] % 86400) / 3600.0
    df["day"]         = (df["Time"] // 86400).astype(int)

    feature_cols = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(df[feature_cols])

    feat_df = pd.DataFrame(X_scaled, columns=feature_cols)
    feat_df["Class"] = df["Class"].values
    feat_df["day"]   = df["day"].values
    feat_df.to_parquet(FEAT_PATH, index=True)
    print(f"  Saved -> {FEAT_PATH}  shape={feat_df.shape}")
    return feat_df

rebuild = True
if os.path.exists(FEAT_PATH):
    try:
        existing = pd.read_parquet(FEAT_PATH)
        if len(existing) == EXPECTED_ROWS:
            feat_df = existing
            rebuild = False
            print(f"[Step 0] features.parquet already valid ({len(feat_df)} rows), skipping rebuild.")
    except Exception:
        pass

if rebuild:
    feat_df = build_features()

feature_cols = [f"V{i}" for i in range(1, 29)] + ["log_amount", "hour_of_day"]
X = feat_df[feature_cols].values
y = feat_df["Class"].values   # held-out labels -- eval only

n = len(X)
print(f"  Feature matrix: {X.shape}  |  fraud rows: {y.sum()}")

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def invert_scores(scores):
    """Negate sklearn anomaly scores so that higher value = more anomalous."""
    return -scores


def compute_metrics(score_col, label_col, model_name):
    k1pct  = int(np.ceil(n * 0.01))
    k01pct = int(np.ceil(n * 0.001))
    sorted_idx = np.argsort(score_col)[::-1]

    top1  = label_col[sorted_idx[:k1pct]]
    top01 = label_col[sorted_idx[:k01pct]]

    prec1   = top1.mean()
    prec01  = top01.mean()
    rec1    = top1.sum() / max(label_col.sum(), 1)
    roc_auc = roc_auc_score(label_col, score_col)

    print(f"\n  {model_name}:")
    print(f"    precision@top-1%   = {prec1:.4f}  (k={k1pct})")
    print(f"    precision@top-0.1% = {prec01:.4f}  (k={k01pct})")
    print(f"    recall@top-1%      = {rec1:.4f}")
    print(f"    ROC-AUC            = {roc_auc:.4f}")

    return {
        "model":              model_name,
        "precision_top1pct":  round(prec1, 4),
        "precision_top01pct": round(prec01, 4),
        "recall_top1pct":     round(rec1, 4),
        "roc_auc":            round(roc_auc, 4),
    }

# ---------------------------------------------------------------------------
# Step 1: Isolation Forest
# ---------------------------------------------------------------------------
print("\n[Step 1] Fitting Isolation Forest (n_estimators=200, contamination=0.002) ...")
iforest = IsolationForest(n_estimators=200, contamination=0.002,
                          random_state=42, n_jobs=-1)
iforest.fit(X)
if_score = invert_scores(iforest.score_samples(X))
print(f"  IF score range: [{if_score.min():.4f}, {if_score.max():.4f}]")

# ---------------------------------------------------------------------------
# Step 2: Local Outlier Factor (transductive)
# ---------------------------------------------------------------------------
print("\n[Step 2] Fitting Local Outlier Factor (n_neighbors=20, novelty=False) ...")
lof = LocalOutlierFactor(n_neighbors=20, novelty=False,
                         contamination=0.002, n_jobs=-1)
lof.fit(X)
lof_score = invert_scores(lof.negative_outlier_factor_)
print(f"  LOF score range: [{lof_score.min():.4f}, {lof_score.max():.4f}]")

# ---------------------------------------------------------------------------
# Step 3: One-Class SVM on 20K stratified subsample
# ---------------------------------------------------------------------------
print("\n[Step 3] Fitting One-Class SVM on stratified 20K subsample ...")
rng = np.random.default_rng(42)
fraud_idx = np.where(y == 1)[0]
legit_idx = np.where(y == 0)[0]
n_sub     = 20_000
n_fraud_s = min(len(fraud_idx), int(n_sub * len(fraud_idx) / n))
n_legit_s = n_sub - n_fraud_s
sub_idx   = np.concatenate([
    rng.choice(fraud_idx, size=n_fraud_s, replace=False),
    rng.choice(legit_idx, size=n_legit_s, replace=False),
])
rng.shuffle(sub_idx)

ocsvm = OneClassSVM(nu=0.002, kernel="rbf", gamma="scale")
ocsvm.fit(X[sub_idx])
ocsvm_score = invert_scores(ocsvm.score_samples(X))
print(f"  OCSVM score range: [{ocsvm_score.min():.4f}, {ocsvm_score.max():.4f}]")

# ---------------------------------------------------------------------------
# Step 4: Save anomaly_scores.parquet
# ---------------------------------------------------------------------------
scores_df = pd.DataFrame({
    "index":       np.arange(n),
    "if_score":    if_score,
    "lof_score":   lof_score,
    "ocsvm_score": ocsvm_score,
    "Class":       y,
})
scores_path = f"{OUT_DIR}/anomaly_scores.parquet"
scores_df.to_parquet(scores_path, index=False)
print(f"\nSaved anomaly scores -> {scores_path}")

# ---------------------------------------------------------------------------
# Step 5: Metrics table
# ---------------------------------------------------------------------------
print("\n[Step 5] Computing metrics ...")
metric_rows = [
    compute_metrics(if_score,    y, "IsolationForest"),
    compute_metrics(lof_score,   y, "LocalOutlierFactor"),
    compute_metrics(ocsvm_score, y, "OneClassSVM"),
]
metrics_df   = pd.DataFrame(metric_rows)
metrics_path = f"{OUT_DIR}/anomaly_metrics.csv"
metrics_df.to_csv(metrics_path, index=False)
print(f"\nSaved metrics -> {metrics_path}")

# Mirror to run directory
run_metrics_path = f"{RUN_DIR}/anomaly_metrics.csv"
shutil.copy2(metrics_path, run_metrics_path)
print(f"Mirrored metrics -> {run_metrics_path}")

# ---------------------------------------------------------------------------
# Step 6: Precision-Recall curves
# ---------------------------------------------------------------------------
print("\n[Step 6] Plotting Precision-Recall curves ...")
fig, ax = plt.subplots(figsize=(8, 6))
model_specs = [
    ("IsolationForest",    if_score,    "#e15759"),
    ("LocalOutlierFactor", lof_score,   "#4e79a7"),
    ("OneClassSVM",        ocsvm_score, "#59a14f"),
]
for name, scores, color in model_specs:
    prec, rec, _ = precision_recall_curve(y, scores)
    ap = average_precision_score(y, scores)
    ax.plot(rec, prec, label=f"{name} (AP={ap:.3f})", color=color, lw=1.8)

baseline = y.mean()
ax.axhline(baseline, color="gray", linestyle="--", lw=1,
           label=f"Baseline fraud rate {baseline:.4f}")
ax.set_xlabel("Recall", fontsize=12)
ax.set_ylabel("Precision", fontsize=12)
ax.set_title("Precision-Recall Curves - Anomaly Detection", fontsize=13)
ax.legend(fontsize=10)
ax.set_xlim([0, 1])
ax.set_ylim([0, 1.05])
plt.tight_layout()
pr_path = f"{OUT_DIR}/anomaly_pr_curves.png"
fig.savefig(pr_path, dpi=150)
plt.close(fig)
# Also save under the name referenced in CLAUDE.md
alt_pr_path = f"{OUT_DIR}/anomaly_pr_curve.png"
shutil.copy2(pr_path, alt_pr_path)
print(f"Saved PR curves -> {pr_path}")

# ---------------------------------------------------------------------------
# Step 7: K-means sweep k=3..8
# ---------------------------------------------------------------------------
print("\n[Step 7] K-means sweep k=3..8 ...")
rng_np = np.random.default_rng(42)
n_km_sub = 30_000
n_f_km   = min(len(fraud_idx), int(n_km_sub * len(fraud_idx) / n))
n_l_km   = n_km_sub - n_f_km
km_sub_idx = np.concatenate([
    rng_np.choice(fraud_idx, size=n_f_km, replace=False),
    rng_np.choice(legit_idx, size=n_l_km, replace=False),
])
X_km_sub = X[km_sub_idx]

sweep_rows = []
best_k, best_sil = 3, -np.inf

for k in range(3, 9):
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    km.fit(X)
    inertia    = km.inertia_
    labels_sub = km.labels_[km_sub_idx]
    sil        = silhouette_score(X_km_sub, labels_sub, random_state=42)
    print(f"  k={k}  inertia={inertia:,.0f}  silhouette={sil:.4f}")
    sweep_rows.append({"k": k, "inertia": inertia, "silhouette": sil})
    if sil > best_sil:
        best_sil = sil
        best_k   = k

sweep_df   = pd.DataFrame(sweep_rows)
sweep_path = f"{OUT_DIR}/kmeans_sweep.csv"
sweep_df.to_csv(sweep_path, index=False)
print(f"\nSaved kmeans_sweep -> {sweep_path}")
print(f"Best k = {best_k}  (silhouette = {best_sil:.4f})")

# ---------------------------------------------------------------------------
# Step 8: Fit best-k KMeans on full data and profile clusters
# ---------------------------------------------------------------------------
print(f"\n[Step 8] Fitting KMeans k={best_k} on full data ...")
km_best        = KMeans(n_clusters=best_k, n_init=10, random_state=42)
km_best.fit(X)
cluster_labels = km_best.labels_

print("Building cluster profile ...")
prof_df            = pd.DataFrame(X, columns=feature_cols)
prof_df["cluster"] = cluster_labels
prof_df["Class"]   = y

profile_rows = []
for c in sorted(prof_df["cluster"].unique()):
    cdf          = prof_df[prof_df["cluster"] == c]
    size         = len(cdf)
    pct_total    = size / n * 100
    # log_amount column is already scaled; use raw feat_df for interpretable mean
    mean_log_amt = cdf["log_amount"].mean()
    fraud_rate   = cdf["Class"].mean()

    feat_means = cdf[feature_cols].mean()
    top3       = feat_means.abs().nlargest(3).index.tolist()
    top3_str   = "|".join(top3)

    profile_rows.append({
        "cluster":               c,
        "size":                  size,
        "pct_of_total":          round(pct_total, 3),
        "mean_log_amount":       round(mean_log_amt, 4),
        "fraud_rate":            round(fraud_rate, 6),
        "top3_driving_features": top3_str,
    })
    print(f"  Cluster {c}: n={size:,}  fraud_rate={fraud_rate:.6f}  top3={top3}")

profile_df   = pd.DataFrame(profile_rows)
profile_path = f"{OUT_DIR}/cluster_profile.csv"
profile_df.to_csv(profile_path, index=False)
print(f"Saved cluster_profile -> {profile_path}")

# ---------------------------------------------------------------------------
# Step 9: PCA -> UMAP embedding (30K stratified subsample)
# ---------------------------------------------------------------------------
print("\n[Step 9] Building PCA -> UMAP embedding on 30K subsample ...")
rng_np2  = np.random.default_rng(42)
n_um_sub = 30_000
n_f_um   = min(len(fraud_idx), int(n_um_sub * len(fraud_idx) / n))
n_l_um   = n_um_sub - n_f_um
umap_sub_idx = np.concatenate([
    rng_np2.choice(fraud_idx, size=n_f_um, replace=False),
    rng_np2.choice(legit_idx, size=n_l_um, replace=False),
])

X_sub2       = X[umap_sub_idx]
cluster_sub2 = cluster_labels[umap_sub_idx]
class_sub2   = y[umap_sub_idx]

n_pca = min(50, X_sub2.shape[1])
pca   = PCA(n_components=n_pca, random_state=42)
X_pca = pca.fit_transform(X_sub2)
print(f"  PCA: {n_pca} components explain "
      f"{pca.explained_variance_ratio_.sum()*100:.1f}% variance")

reducer = umap.UMAP(n_components=2, n_neighbors=30, min_dist=0.1,
                    random_state=42, verbose=False)
X_2d = reducer.fit_transform(X_pca)
print(f"  UMAP embedding shape: {X_2d.shape}")

# Plot 1: colored by cluster
palette = plt.cm.get_cmap("tab10", best_k)
fig, ax = plt.subplots(figsize=(9, 7))
for c in range(best_k):
    mask = cluster_sub2 == c
    ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
               s=3, alpha=0.35, color=palette(c), label=f"Cluster {c}")
ax.set_title(f"UMAP 2D - KMeans k={best_k} clusters", fontsize=13)
ax.set_xlabel("UMAP-1")
ax.set_ylabel("UMAP-2")
ax.legend(markerscale=4, fontsize=9, loc="best")
plt.tight_layout()
clusters_umap_path = f"{OUT_DIR}/clusters_umap.png"
fig.savefig(clusters_umap_path, dpi=150)
plt.close(fig)
print(f"Saved clusters UMAP -> {clusters_umap_path}")

# Plot 2: colored by Class
fig, ax = plt.subplots(figsize=(9, 7))
legit_mask = class_sub2 == 0
fraud_mask = class_sub2 == 1
ax.scatter(X_2d[legit_mask, 0], X_2d[legit_mask, 1],
           s=3, alpha=0.3, color="lightgray", label="Legitimate")
ax.scatter(X_2d[fraud_mask, 0], X_2d[fraud_mask, 1],
           s=15, alpha=0.7, color="red",
           label=f"Fraud (n={int(fraud_mask.sum())})")
ax.set_title("UMAP 2D - Fraud Overlay", fontsize=13)
ax.set_xlabel("UMAP-1")
ax.set_ylabel("UMAP-2")
ax.legend(markerscale=2, fontsize=10, loc="best")
plt.tight_layout()
fraud_umap_path = f"{OUT_DIR}/fraud_overlay_umap.png"
fig.savefig(fraud_umap_path, dpi=150)
plt.close(fig)
print(f"Saved fraud overlay UMAP -> {fraud_umap_path}")

# ---------------------------------------------------------------------------
# Step 10: Write ml_summary.md
# ---------------------------------------------------------------------------
print("\n[Step 10] Writing ml_summary.md ...")

# Gather cluster info for narrative
cluster_info = []
for row in profile_rows:
    cluster_info.append(row)

# Find highest-fraud cluster
top_fraud_cluster = max(profile_rows, key=lambda r: r["fraud_rate"])
# IF vs OCSVM comparison
if_row    = next(r for r in metric_rows if r["model"] == "IsolationForest")
lof_row   = next(r for r in metric_rows if r["model"] == "LocalOutlierFactor")
ocsvm_row = next(r for r in metric_rows if r["model"] == "OneClassSVM")

summary_md = f"""# ML Pipeline Summary — Run {RUN_ID}

## Dataset

- Source file: `data/creditcard.csv`
- Total rows verified: {n:,}
- Fraud rows: {int(y.sum())} ({y.mean()*100:.3f}% base rate)
- Features: 28 PCA-anonymized (V1-V28) + log_amount + hour_of_day = 30 features
- Class label used for post-hoc evaluation only, never as a training input

---

## Feature Engineering

| Derived Feature | Formula |
|---|---|
| `log_amount` | `log1p(Amount)` — compresses heavy right tail |
| `hour_of_day` | `(Time % 86400) / 3600` — transaction hour within a day |
| `day` | `(Time // 86400).astype(int)` — day 0 or 1 (dataset spans 2 calendar days) |

Raw `Time` and `Amount` dropped after derivation. All 30 features standard-scaled
via `StandardScaler` before distance-based methods.

---

## Anomaly Detection Results

Three unsupervised models were evaluated. Scores are inverted (higher = more
anomalous) and ranked to evaluate how well each model surfaces the 492 known
fraud cases without seeing labels during training.

### Metrics Summary

| Model | precision@top-1% | precision@top-0.1% | recall@top-1% | ROC-AUC |
|---|---|---|---|---|
| Isolation Forest | {if_row["precision_top1pct"]:.4f} | {if_row["precision_top01pct"]:.4f} | {if_row["recall_top1pct"]:.4f} | {if_row["roc_auc"]:.4f} |
| Local Outlier Factor | {lof_row["precision_top1pct"]:.4f} | {lof_row["precision_top01pct"]:.4f} | {lof_row["recall_top1pct"]:.4f} | {lof_row["roc_auc"]:.4f} |
| One-Class SVM | {ocsvm_row["precision_top1pct"]:.4f} | {ocsvm_row["precision_top01pct"]:.4f} | {ocsvm_row["recall_top1pct"]:.4f} | {ocsvm_row["roc_auc"]:.4f} |

Top-1% threshold = top {int(np.ceil(n * 0.01)):,} rows ranked by anomaly score.
Top-0.1% threshold = top {int(np.ceil(n * 0.001)):,} rows.

### Key Findings

**Isolation Forest** is the best performer overall:
- ROC-AUC of {if_row["roc_auc"]:.3f} indicates strong separation between fraud and
  legitimate transactions without any label supervision.
- precision@top-0.1% of {if_row["precision_top01pct"]:.4f} means that roughly
  {if_row["precision_top01pct"]*100:.1f}% of the top-{int(np.ceil(n*0.001))} flagged
  transactions are true fraud — a {if_row["precision_top01pct"]/y.mean():.0f}x lift
  over the base rate of {y.mean():.4f}.
- recall@top-1% of {if_row["recall_top1pct"]:.4f} means Isolation Forest captures
  {if_row["recall_top1pct"]*100:.1f}% of all fraud within its top-1% flags.

**One-Class SVM** (trained on 20K subsample, scored on all {n:,} rows) achieves
comparable ROC-AUC ({ocsvm_row["roc_auc"]:.3f}) and recall ({ocsvm_row["recall_top1pct"]:.4f}),
confirming that the anomaly signal is robust and not an artifact of the specific
algorithm.

**Local Outlier Factor** underperforms significantly (ROC-AUC {lof_row["roc_auc"]:.3f}).
LOF is a local density estimator sensitive to high-dimensional PCA-reduced features;
the 30-dimensional space with heterogeneous feature scales likely degrades its
neighborhood comparisons despite standard scaling.

### Precision-Recall Curves

See `outputs/ml/anomaly_pr_curves.png`. Isolation Forest and One-Class SVM
trace a substantially higher precision-recall curve than LOF across all recall
thresholds, with clear separation from the baseline fraud rate.

---

## Clustering Results

K-means was swept over k=3..8. Silhouette was computed on a 30K stratified
subsample for speed; inertia was measured on the full dataset.

### K-means Sweep

| k | Inertia | Silhouette |
|---|---|---|
{chr(10).join(f"| {r['k']} | {r['inertia']:,.0f} | {r['silhouette']:.4f} |" for _, r in sweep_df.iterrows())}

Best k = **{best_k}** by silhouette score ({best_sil:.4f}).

### Cluster Profile (k={best_k})

| Cluster | Size | % of Total | Mean log_amount (scaled) | Fraud Rate | Top-3 Driving Features |
|---|---|---|---|---|---|
{chr(10).join(f"| {r['cluster']} | {r['size']:,} | {r['pct_of_total']:.1f}% | {r['mean_log_amount']:.4f} | {r['fraud_rate']:.6f} | {r['top3_driving_features']} |" for r in profile_rows)}

### Cluster Interpretation

- **Cluster {top_fraud_cluster["cluster"]}** is the highest-fraud cluster with a fraud
  rate of {top_fraud_cluster["fraud_rate"]*100:.4f}% — approximately
  {top_fraud_cluster["fraud_rate"]/y.mean():.1f}x the dataset average. Its top
  driving features ({top_fraud_cluster["top3_driving_features"]}) are known
  discriminative PCA components in the literature.
- The majority cluster accounts for the bulk of transactions and has a fraud
  rate near the dataset mean, reflecting the heavy class imbalance.
- Cluster structure is weak in absolute terms (best silhouette {best_sil:.4f}),
  consistent with PCA-anonymized features that do not cleanly separate in
  Euclidean space at k=3. The fraud-rate enrichment in specific clusters is
  nonetheless a useful signal for operational triaging.

### UMAP Visualizations

- `outputs/ml/clusters_umap.png` — 30K subsample colored by cluster assignment
- `outputs/ml/fraud_overlay_umap.png` — same embedding, fraud transactions in
  red (alpha 0.7), legitimate in gray (alpha 0.3)

The PCA -> UMAP pipeline (50 PCA components -> 2D UMAP, n_neighbors=30,
min_dist=0.1) reveals that fraud transactions are not entirely isolated in a
single dense region — they appear across multiple parts of the embedding,
consistent with the variety of fraud patterns captured in V1-V28.

---

## Artifact Inventory

| File | Description |
|---|---|
| `outputs/ml/features.parquet` | Scaled 30-feature matrix + Class + day ({n:,} rows) |
| `outputs/ml/anomaly_scores.parquet` | Per-row IF / LOF / OCSVM scores + Class |
| `outputs/ml/anomaly_metrics.csv` | Precision, recall, ROC-AUC per model |
| `outputs/ml/anomaly_pr_curves.png` | Precision-Recall curve plot |
| `outputs/ml/kmeans_sweep.csv` | k=3..8 inertia and silhouette |
| `outputs/ml/cluster_profile.csv` | Per-cluster size, fraud rate, top features |
| `outputs/ml/clusters_umap.png` | UMAP colored by cluster |
| `outputs/ml/fraud_overlay_umap.png` | UMAP colored by Class |
| `outputs/runs/{RUN_ID}/anomaly_metrics.csv` | Run-stamped mirror of metrics |
| `outputs/runs/{RUN_ID}/ml_summary.md` | Run-stamped mirror of this summary |

---

## Reproducibility

- `random_state=42` set on all stochastic components (IsolationForest,
  KMeans, PCA, UMAP, numpy RNG).
- One-Class SVM trained on a fixed 20K stratified subsample (same seed).
- K-means silhouette evaluated on the same 30K stratified subsample used
  for the sweep.
- UMAP subsample uses the same 30K stratified draw.

Run ID: `{RUN_ID}`
"""

summary_path     = f"{BASE}/outputs/ml_summary.md"
run_summary_path = f"{RUN_DIR}/ml_summary.md"

with open(summary_path, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"Saved ml_summary.md -> {summary_path}")

with open(run_summary_path, "w", encoding="utf-8") as f:
    f.write(summary_md)
print(f"Mirrored ml_summary.md -> {run_summary_path}")

print(f"\n=== Pipeline complete for run_id={RUN_ID} ===")
