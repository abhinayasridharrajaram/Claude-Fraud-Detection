"""
02_clustering.py
K-means sweep k=3..8, cluster profiling, UMAP 2-D visualization.
Outputs:
  outputs/ml/kmeans_sweep.csv
  outputs/ml/cluster_profile.csv
  outputs/ml/clusters_umap.png
  outputs/ml/fraud_overlay_umap.png
"""

import sys
import os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import umap

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
X  = feat_df[feature_cols].values
y  = feat_df["Class"].values   # eval only

n       = len(X)
rng_np  = np.random.default_rng(42)

# ----------------------------------------------------------------------------?
# 1. K-means sweep k=3..8
# ----------------------------------------------------------------------------?
# Use a 30K stratified subsample for silhouette (speed)
fraud_idx = np.where(y == 1)[0]
legit_idx = np.where(y == 0)[0]
n_sub     = 30_000
n_f       = min(len(fraud_idx), int(n_sub * len(fraud_idx) / n))
n_l       = n_sub - n_f
sub_idx   = np.concatenate([
    rng_np.choice(fraud_idx, size=n_f, replace=False),
    rng_np.choice(legit_idx, size=n_l, replace=False),
])
X_sub = X[sub_idx]

print("\nK-means sweep ?")
sweep_rows = []
best_k, best_sil = 3, -np.inf

for k in range(3, 9):
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    km.fit(X)
    inertia = km.inertia_
    # silhouette on 30K subsample
    labels_sub = km.labels_[sub_idx]
    sil = silhouette_score(X_sub, labels_sub, random_state=42)
    print(f"  k={k}  inertia={inertia:,.0f}  silhouette={sil:.4f}")
    sweep_rows.append({"k": k, "inertia": inertia, "silhouette": sil})
    if sil > best_sil:
        best_sil = sil
        best_k   = k

sweep_df = pd.DataFrame(sweep_rows)
sweep_path = f"{OUT_DIR}/kmeans_sweep.csv"
sweep_df.to_csv(sweep_path, index=False)
print(f"\nSaved sweep -> {sweep_path}")
print(f"Best k by silhouette: k={best_k}  (silhouette={best_sil:.4f})")

# ----------------------------------------------------------------------------?
# 2. Fit best-k model on full data
# ----------------------------------------------------------------------------?
print(f"\nFitting KMeans k={best_k} on full {n} rows ?")
km_best = KMeans(n_clusters=best_k, n_init=10, random_state=42)
km_best.fit(X)
cluster_labels = km_best.labels_

# ----------------------------------------------------------------------------?
# 3. Cluster profile
# ----------------------------------------------------------------------------?
print("Building cluster profile ?")
# Attach raw (scaled) features + metadata
prof_df = pd.DataFrame(X, columns=feature_cols)
prof_df["cluster"]     = cluster_labels
prof_df["Class"]       = y
prof_df["log_amount"]  = feat_df["log_amount"].values   # already scaled col

profile_rows = []
for c in sorted(prof_df["cluster"].unique()):
    cdf = prof_df[prof_df["cluster"] == c]
    size         = len(cdf)
    pct_total    = size / n * 100
    mean_log_amt = cdf["log_amount"].mean()
    fraud_rate   = cdf["Class"].mean()

    # Top-3 driving features: highest |mean z-score| among V1..V28, log_amount, hour_of_day
    feat_means = cdf[feature_cols].mean()
    top3 = feat_means.abs().nlargest(3).index.tolist()
    top3_str = "|".join(top3)

    profile_rows.append({
        "cluster":             c,
        "size":                size,
        "pct_of_total":        round(pct_total, 3),
        "mean_log_amount":     round(mean_log_amt, 4),
        "fraud_rate":          round(fraud_rate, 6),
        "top3_driving_features": top3_str,
    })
    print(f"  Cluster {c}: n={size:,}  fraud_rate={fraud_rate:.4f}  top3={top3}")

profile_df = pd.DataFrame(profile_rows)
profile_path = f"{OUT_DIR}/cluster_profile.csv"
profile_df.to_csv(profile_path, index=False)
print(f"Saved cluster profile -> {profile_path}")

# ----------------------------------------------------------------------------?
# 4. UMAP 2-D embedding on 30K stratified subsample
#    Pipeline: PCA (50 components) -> UMAP (2D)
# ----------------------------------------------------------------------------?
print("\nBuilding PCA -> UMAP embedding on 30K subsample ?")

# Fresh stratified 30K subsample (reproducible)
rng_np2 = np.random.default_rng(42)
n_f2    = min(len(fraud_idx), int(n_sub * len(fraud_idx) / n))
n_l2    = n_sub - n_f2
sub_idx2 = np.concatenate([
    rng_np2.choice(fraud_idx, size=n_f2, replace=False),
    rng_np2.choice(legit_idx, size=n_l2, replace=False),
])

X_sub2          = X[sub_idx2]
cluster_sub2    = cluster_labels[sub_idx2]
class_sub2      = y[sub_idx2]

# PCA -> 50 components
n_pca = min(50, X_sub2.shape[1])
pca   = PCA(n_components=n_pca, random_state=42)
X_pca = pca.fit_transform(X_sub2)
print(f"  PCA variance explained ({n_pca} components): "
      f"{pca.explained_variance_ratio_.sum()*100:.1f}%")

# UMAP -> 2D
reducer = umap.UMAP(n_components=2, n_neighbors=30, min_dist=0.1,
                    random_state=42, verbose=False)
X_2d = reducer.fit_transform(X_pca)
print(f"  UMAP embedding shape: {X_2d.shape}")

# ----------------------------------------------------------------------------?
# 5. Plot 1: color by cluster
# ----------------------------------------------------------------------------?
palette = plt.cm.get_cmap("tab10", best_k)
fig, ax = plt.subplots(figsize=(9, 7))
for c in range(best_k):
    mask = cluster_sub2 == c
    ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
               s=3, alpha=0.35, color=palette(c), label=f"Cluster {c}")
ax.set_title(f"UMAP 2D ? KMeans k={best_k} clusters", fontsize=13)
ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
ax.legend(markerscale=4, fontsize=9, loc="best")
plt.tight_layout()
clusters_umap_path = f"{OUT_DIR}/clusters_umap.png"
fig.savefig(clusters_umap_path, dpi=150)
plt.close(fig)
print(f"Saved cluster UMAP -> {clusters_umap_path}")

# ----------------------------------------------------------------------------?
# 6. Plot 2: color by Class (fraud red, legit gray)
# ----------------------------------------------------------------------------?
fig, ax = plt.subplots(figsize=(9, 7))
legit_mask = class_sub2 == 0
fraud_mask = class_sub2 == 1
ax.scatter(X_2d[legit_mask, 0], X_2d[legit_mask, 1],
           s=3, alpha=0.3, color="lightgray", label="Legitimate")
ax.scatter(X_2d[fraud_mask, 0], X_2d[fraud_mask, 1],
           s=15, alpha=0.7, color="red", label=f"Fraud (n={fraud_mask.sum()})")
ax.set_title("UMAP 2D ? Fraud Overlay", fontsize=13)
ax.set_xlabel("UMAP-1"); ax.set_ylabel("UMAP-2")
ax.legend(markerscale=2, fontsize=10, loc="best")
plt.tight_layout()
fraud_umap_path = f"{OUT_DIR}/fraud_overlay_umap.png"
fig.savefig(fraud_umap_path, dpi=150)
plt.close(fig)
print(f"Saved fraud overlay UMAP -> {fraud_umap_path}")

print("\nDone ? clustering complete.")
