# Claude Code — Credit Card Fraud Detection

## Project

Unsupervised anomaly detection and clustering on the Kaggle Credit Card Fraud
dataset. The goal is to surface likely-fraudulent transactions **without using
the `Class` label during training**, then evaluate performance against that
held-out label.

## Data

- **File:** `data/creditcard.csv` (~150 MB, 284,807 rows, 31 columns)
- **Source:** https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- **Schema:**
  - `Time` — seconds elapsed from the first transaction (2 calendar days total)
  - `V1` … `V28` — anonymized features (already PCA-transformed)
  - `Amount` — transaction amount (USD, heavy right tail)
  - `Class` — 1 = fraud (492 rows, 0.172%), 0 = legitimate
- **Evaluation-only column:** `Class`. **Never** include `Class` as an input
  feature to clustering or anomaly models.

## SQL / Compute

- DuckDB in-process (no server, no auth). Load the CSV directly:
  `duckdb.connect().execute("SELECT * FROM 'data/creditcard.csv'")`
- Python 3.10+, scikit-learn, umap-learn, matplotlib, pandas, pyarrow.

## Feature engineering conventions

- `log_amount = log1p(Amount)` — Amount is heavy-tailed.
- `hour_of_day = (Time % 86400) / 3600.0`
- `day = (Time // 86400).astype(int)` — dataset spans 2 days.
- Drop raw `Time` and raw `Amount` from feature matrix after deriving above.
- Standard-scale all features (`StandardScaler`) before distance-based methods.

## ML conventions

- **Primary task:** anomaly detection. Models to try: Isolation Forest
  (`contamination=0.002`), Local Outlier Factor (`novelty=False`), One-Class SVM
  (on a 20K sample — it doesn't scale). Score all 284K rows, rank by anomaly
  score, evaluate top-k against `Class`.
- **Secondary task:** clustering. K-means sweep `k=3..8`, pick by silhouette.
  Profile each cluster: size, mean `log_amount`, fraud rate, top 3 driving
  features (highest |mean z-score|). Overlay fraud rate as a cluster attribute,
  not a training input.
- **Dim-reduction for plots:** PCA → 50 components → UMAP → 2D. Color points
  by cluster in one plot, by `Class` in a second plot.
- **Metrics to always report:**
  - `precision@top-1%` (2,848 highest-scored rows)
  - `precision@top-0.1%` (285 highest-scored rows)
  - `recall@top-1%`
  - ROC-AUC of the anomaly score vs `Class`

## Output layout

- `sql/NN_*.sql` — DuckDB queries used during EDA.
- `outputs/eda_summary.md` — profiling narrative.
- `outputs/ml/anomaly_scores.parquet` — per-row (index, if_score, lof_score, ocsvm_score).
- `outputs/ml/cluster_profile.csv` — one row per cluster with size, means, fraud rate.
- `outputs/ml/anomaly_pr_curve.png`
- `outputs/ml/clusters_umap.png`
- `outputs/ml_summary.md` — ML narrative with metrics.
- `outputs/report.md` — final polished writeup (produced by `insight-writer`).
- `outputs/runs/<run_id>/data_quality_report.md` — data-validator output
- `outputs/runs/<run_id>/lineage.json` — input fingerprint
- `outputs/runs/<run_id>/feature_stats.parquet` — per-run distribution stats
- `outputs/ml/supervised_metrics.csv` — supervised baseline metrics
- `outputs/ml_supervised_comparison.md` — supervised vs unsupervised writeup
- `outputs/threshold_decisions.md` — append-only threshold audit log
- `outputs/compare_<a>_vs_<b>.md` — per-comparison run diff

## Run stamping and audit trail

Every pipeline invocation is stamped with a `run_id` of the form
`YYYY-MM-DD_HHMM`. The fraud-analyst skill writes this id to
`outputs/runs/current_run_id.txt` at the start of each run, and all sub-agents
write their artifacts both to `outputs/<latest>.md` (mirrors of the most
recent run) and to `outputs/runs/<run_id>/` (immutable per-run record).

**Never overwrite a stamped run directory.** If a file already exists in
`outputs/runs/<run_id>/`, append a suffix rather than overwrite — stamped
runs are audit evidence.

Lineage metadata (file SHA-256, row count, git SHA, library versions) lives
in `outputs/lineage.json` (latest) and `outputs/runs/<run_id>/lineage.json`
(per-run). This is the evidence trail that confirms which inputs produced
which outputs.

## Security rules

- No `curl`, `wget`, `Invoke-WebRequest`, or `Invoke-RestMethod`. All data is
  local; no network calls are needed after the initial CSV download.
- No secrets or tokens anywhere in the repo.
- No `rm -rf` / `Remove-Item -Recurse -Force` — deletions must be explicit.
- Writes are restricted to `sql/`, `ml/`, `outputs/`, and `data/` (for derived
  parquet only — never overwrite `data/creditcard.csv`).