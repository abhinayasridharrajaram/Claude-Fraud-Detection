"""
01_trip_archetypes.py
K-means trip archetype clustering on NYC Yellow Cab sample.

Input  : C:/Users/Abhi/claude-bigquery-copilot/data/pages/b*.csv
Output : outputs/ml/trip_archetypes.png        (elbow + silhouette plot)
         outputs/ml/trip_archetypes_profile.csv (cluster profiles)

Run    : python ml/01_trip_archetypes.py
"""

import os
import sys
import glob
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = "C:/Users/Abhi/claude-bigquery-copilot"
PAGES_DIR  = os.path.join(BASE_DIR, "data", "pages")
OUT_DIR    = os.path.join(BASE_DIR, "outputs", "ml")
PLOT_PATH  = os.path.join(OUT_DIR, "trip_archetypes.png")
PROF_PATH  = os.path.join(OUT_DIR, "trip_archetypes_profile.csv")

os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load all pages
# ---------------------------------------------------------------------------
page_files = sorted(glob.glob(os.path.join(PAGES_DIR, "b*.csv")))
if not page_files:
    sys.exit(f"ERROR: No b*.csv files found in {PAGES_DIR}")

print(f"Found {len(page_files)} page file(s): {[os.path.basename(f) for f in page_files]}")

df = pd.concat([pd.read_csv(f) for f in page_files], ignore_index=True)
total_rows = len(df)
print(f"Loaded {total_rows:,} rows.")

TARGET_ROWS = 200_000
if total_rows < TARGET_ROWS * 0.9:
    print(
        f"WARNING: Sample has {total_rows:,} rows — below the 90% threshold of "
        f"{int(TARGET_ROWS * 0.9):,} rows target ({TARGET_ROWS:,}). "
        "Results are illustrative only. Re-run after collecting full MCP pages."
    )

EXPECTED_COLS = [
    "log_fare", "log_distance", "trip_duration_min",
    "tip_pct", "hour_of_day", "passenger_count", "is_airport",
]
missing = [c for c in EXPECTED_COLS if c not in df.columns]
if missing:
    sys.exit(f"ERROR: Missing expected columns: {missing}")

# ---------------------------------------------------------------------------
# 2. Drop rows where log_distance or tip_pct is null
# ---------------------------------------------------------------------------
before = len(df)
df = df.dropna(subset=["log_distance", "tip_pct"])
after = len(df)
print(f"Dropped {before - after:,} rows with null log_distance or tip_pct. "
      f"Remaining: {after:,} rows.")

if after < 10:
    sys.exit(f"ERROR: Only {after} rows remain after null-drop — cannot cluster.")

# ---------------------------------------------------------------------------
# 3. Feature matrix + Z-scaling
# ---------------------------------------------------------------------------
FEATURES = [
    "log_fare", "log_distance", "trip_duration_min",
    "tip_pct", "hour_of_day", "passenger_count", "is_airport",
]

X_raw = df[FEATURES].values
scaler = StandardScaler()
X = scaler.fit_transform(X_raw)

print(f"Feature matrix shape: {X.shape}")

# ---------------------------------------------------------------------------
# 4. k-means sweep k in [3..8]
# ---------------------------------------------------------------------------
K_RANGE = range(3, 9)
inertias = []
silhouettes = []

print("\nSweeping k in [3..8] ...")
for k in K_RANGE:
    km = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = km.fit_predict(X)
    inertias.append(km.inertia_)
    if len(set(labels)) > 1:
        sil = silhouette_score(X, labels, sample_size=min(5000, after), random_state=42)
    else:
        sil = -1.0
    silhouettes.append(sil)
    print(f"  k={k}  inertia={km.inertia_:,.1f}  silhouette={sil:.4f}")

# ---------------------------------------------------------------------------
# 5. Pick best k by silhouette
# ---------------------------------------------------------------------------
best_idx  = int(np.argmax(silhouettes))
best_k    = list(K_RANGE)[best_idx]
best_sil  = silhouettes[best_idx]
print(f"\nBest k = {best_k}  (silhouette = {best_sil:.4f})")

# ---------------------------------------------------------------------------
# 6. Fit final KMeans at best k
# ---------------------------------------------------------------------------
km_final = KMeans(n_clusters=best_k, n_init=10, random_state=42)
df["cluster"] = km_final.fit_predict(X)
print(f"Final KMeans fitted. Cluster sizes:\n{df['cluster'].value_counts().sort_index()}")

# ---------------------------------------------------------------------------
# 7. Elbow + silhouette plot
# ---------------------------------------------------------------------------
k_vals = list(K_RANGE)

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("NYC Taxi Trip Archetypes — k-Means Diagnostics", fontsize=14, fontweight="bold")

# Elbow plot
ax1 = axes[0]
ax1.plot(k_vals, inertias, marker="o", color="steelblue", linewidth=2)
ax1.axvline(best_k, color="crimson", linestyle="--", label=f"Best k={best_k}")
ax1.set_xlabel("Number of clusters (k)", fontsize=11)
ax1.set_ylabel("Inertia (within-cluster SSE)", fontsize=11)
ax1.set_title("Elbow Curve", fontsize=12)
ax1.set_xticks(k_vals)
ax1.legend()
ax1.grid(True, alpha=0.3)

# Silhouette plot
ax2 = axes[1]
colors = ["crimson" if k == best_k else "steelblue" for k in k_vals]
bars = ax2.bar(k_vals, silhouettes, color=colors, edgecolor="white", linewidth=0.5)
ax2.set_xlabel("Number of clusters (k)", fontsize=11)
ax2.set_ylabel("Silhouette Score", fontsize=11)
ax2.set_title("Silhouette Score by k", fontsize=12)
ax2.set_xticks(k_vals)
ax2.set_ylim(0, max(silhouettes) * 1.2 if max(silhouettes) > 0 else 1)
ax2.grid(True, alpha=0.3, axis="y")

# Annotate best bar
best_bar = bars[best_idx]
ax2.annotate(
    f"Best\nk={best_k}\n{best_sil:.3f}",
    xy=(best_bar.get_x() + best_bar.get_width() / 2, best_sil),
    xytext=(0, 10), textcoords="offset points",
    ha="center", fontsize=9, color="crimson",
    arrowprops=dict(arrowstyle="->", color="crimson"),
)

plt.tight_layout()
plt.savefig(PLOT_PATH, dpi=150, bbox_inches="tight")
plt.close()
print(f"\nPlot saved to {PLOT_PATH}")

# ---------------------------------------------------------------------------
# 8. Cluster profile
# ---------------------------------------------------------------------------
profile = (
    df.groupby("cluster")[FEATURES]
    .agg(["mean", "median"])
)
# Flatten multi-level columns
profile.columns = ["_".join(col) for col in profile.columns]

# Add size and share
counts = df["cluster"].value_counts().sort_index().rename("trip_count")
profile = profile.join(counts)
profile["share_pct"] = (profile["trip_count"] / len(df) * 100).round(2)

# Assign plain-English labels based on cluster centroids (back-transformed)
# We use the mean scaled features and the original-scale means for labeling
orig_means = df.groupby("cluster")[FEATURES].mean()

def assign_label(row):
    """Heuristic labeling based on original-scale cluster means."""
    lf   = row["log_fare"]          # LN(fare)
    ld   = row["log_distance"]      # LN(distance)
    dur  = row["trip_duration_min"]
    tip  = row["tip_pct"]
    hr   = row["hour_of_day"]
    ap   = row["is_airport"]

    if ap > 0.3:
        return "Airport runs"
    if lf > 3.2 and dur > 30:
        return "Long premium rides"
    if dur <= 10 and ld < 0.5:
        return "Short urban hops"
    if hr >= 22 or hr <= 4:
        return "Late-night rides"
    if tip > 0.25 and lf > 2.5:
        return "High-tip daytime"
    return "Standard weekday commutes"

labels_map = {c: assign_label(orig_means.loc[c]) for c in orig_means.index}
profile["label"] = profile.index.map(labels_map)

# Reorder columns for readability
first_cols = ["label", "trip_count", "share_pct"]
other_cols = [c for c in profile.columns if c not in first_cols]
profile = profile[first_cols + other_cols]

profile.to_csv(PROF_PATH)
print(f"Profile saved to {PROF_PATH}")

# ---------------------------------------------------------------------------
# 9. Print cluster profiles to stdout
# ---------------------------------------------------------------------------
print("\n" + "=" * 80)
print("CLUSTER PROFILES")
print("=" * 80)

display_cols = [
    "label", "trip_count", "share_pct",
    "log_fare_mean", "log_distance_mean", "trip_duration_min_mean",
    "tip_pct_mean", "hour_of_day_mean", "is_airport_mean",
]
display_cols = [c for c in display_cols if c in profile.columns]

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:.3f}".format)
print(profile[display_cols].to_string())

print("\n" + "=" * 80)
print(f"Data note: {total_rows:,} raw rows loaded, {after:,} after null-drop.")
print(f"Best k = {best_k} chosen by silhouette score ({best_sil:.4f}).")
if total_rows < TARGET_ROWS * 0.9:
    print(
        "CAUTION: Results based on a very small sample. "
        "Re-collect full 200K rows via MCP for production-quality archetypes."
    )
print("=" * 80)
