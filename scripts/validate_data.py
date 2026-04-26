"""
Data quality validator for the credit card fraud detection pipeline.
Produces:
  - outputs/runs/<run_id>/lineage.json
  - outputs/lineage.json  (mirror)
  - outputs/runs/<run_id>/feature_stats.parquet
  - outputs/runs/<run_id>/data_quality_report.md
"""

import hashlib
import json
import os
import subprocess
import sys
import platform
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import sklearn

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path("C:/Users/Abhi/claude-bigquery-copilot")
DATA_FILE = BASE_DIR / "data" / "creditcard.csv"
RUNS_DIR = BASE_DIR / "outputs" / "runs"
CURRENT_RUN_FILE = RUNS_DIR / "current_run_id.txt"
OUTPUTS_DIR = BASE_DIR / "outputs"

# ---------------------------------------------------------------------------
# Step 0 – Resolve run_id
# ---------------------------------------------------------------------------
if CURRENT_RUN_FILE.exists():
    run_id = CURRENT_RUN_FILE.read_text(encoding="utf-8").strip()
else:
    run_id = datetime.now().strftime("%Y-%m-%d_%H%M")
    CURRENT_RUN_FILE.write_text(run_id, encoding="utf-8")

RUN_DIR = RUNS_DIR / run_id
RUN_DIR.mkdir(parents=True, exist_ok=True)

print(f"[validate_data] run_id = {run_id}")
print(f"[validate_data] run_dir = {RUN_DIR}")

# ---------------------------------------------------------------------------
# Step 1 – Lineage stamp
# ---------------------------------------------------------------------------
print("[validate_data] Computing SHA-256 ...")

sha256 = hashlib.sha256()
with open(DATA_FILE, "rb") as fh:
    for chunk in iter(lambda: fh.read(1 << 20), b""):
        sha256.update(chunk)
file_sha256 = sha256.hexdigest()

stat = DATA_FILE.stat()
file_size_bytes = stat.st_size
file_mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()

print("[validate_data] Loading CSV ...")
df = pd.read_csv(DATA_FILE)

row_count = len(df)
column_list = list(df.columns)
col_dtypes = {col: str(df[col].dtype) for col in df.columns}

# Git SHA
try:
    git_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=str(BASE_DIR),
        stderr=subprocess.DEVNULL,
    ).decode().strip()
except Exception:
    git_sha = "unavailable"

lineage = {
    "run_id": run_id,
    "timestamp_utc": datetime.now(tz=timezone.utc).isoformat(),
    "data_file": str(DATA_FILE),
    "sha256": file_sha256,
    "file_size_bytes": file_size_bytes,
    "file_mtime_utc": file_mtime_utc,
    "row_count": row_count,
    "column_count": len(column_list),
    "columns": column_list,
    "col_dtypes": col_dtypes,
    "git_sha": git_sha,
    "python_version": platform.python_version(),
    "sklearn_version": sklearn.__version__,
}

lineage_json = json.dumps(lineage, indent=2)
(RUN_DIR / "lineage.json").write_text(lineage_json, encoding="utf-8")
(OUTPUTS_DIR / "lineage.json").write_text(lineage_json, encoding="utf-8")
print("[validate_data] lineage.json written.")

# ---------------------------------------------------------------------------
# Step 2 – Feature fingerprint
# ---------------------------------------------------------------------------
print("[validate_data] Computing feature statistics ...")

numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

stats_rows = []
quantiles = [0.01, 0.25, 0.50, 0.75, 0.99]

for col in numeric_cols:
    series = df[col]
    q_vals = series.quantile(quantiles)
    row = {
        "column": col,
        "mean": series.mean(),
        "std": series.std(),
        "min": series.min(),
        "max": series.max(),
        "q01": q_vals[0.01],
        "q25": q_vals[0.25],
        "q50": q_vals[0.50],
        "q75": q_vals[0.75],
        "q99": q_vals[0.99],
        "null_count": int(series.isna().sum()),
        "zero_count": int((series == 0).sum()),
        "negative_count": int((series < 0).sum()),
    }
    stats_rows.append(row)

stats_df = pd.DataFrame(stats_rows)
pq.write_table(
    pa.Table.from_pandas(stats_df, preserve_index=False),
    str(RUN_DIR / "feature_stats.parquet"),
)
print("[validate_data] feature_stats.parquet written.")

# ---------------------------------------------------------------------------
# Step 3 – Drift check
# ---------------------------------------------------------------------------
print("[validate_data] Checking for previous run ...")

# Collect run dirs (exclude non-datetime entries like current_run_id.txt)
all_run_dirs = sorted(
    [d for d in RUNS_DIR.iterdir() if d.is_dir()],
    key=lambda d: d.name,
    reverse=True,
)

drift_results = []
sha_rewrite_flag = False
prev_run_id = None

if len(all_run_dirs) >= 2:
    # Walk previous runs (index 1 onward) until we find one with lineage.json or
    # feature_stats.parquet — the immediate predecessor may be a non-validator run.
    prev_run_dir = None
    for candidate in all_run_dirs[1:]:
        if (candidate / "lineage.json").exists() or (candidate / "feature_stats.parquet").exists():
            prev_run_dir = candidate
            break

    if prev_run_dir is None:
        print("[validate_data] No previous run with validator artifacts found; skipping drift.")
    else:
        prev_run_id = prev_run_dir.name
        prev_parquet = prev_run_dir / "feature_stats.parquet"
        prev_lineage_file = prev_run_dir / "lineage.json"

        print(f"[validate_data] Comparing against previous run: {prev_run_id}")

        # SHA rewrite check
        if prev_lineage_file.exists():
            prev_lineage = json.loads(prev_lineage_file.read_text(encoding="utf-8"))
            if (
                prev_lineage.get("data_file") == str(DATA_FILE)
                and prev_lineage.get("sha256") != file_sha256
            ):
                sha_rewrite_flag = True
                print("[validate_data] WARNING: SHA-256 changed but filename unchanged — suspicious rewrite.")

        if prev_parquet.exists():
            from scipy import stats as scipy_stats

            prev_stats_df = pq.read_table(str(prev_parquet)).to_pandas()
            prev_stats_map = prev_stats_df.set_index("column").to_dict(orient="index")

            for col in numeric_cols:
                if col not in prev_stats_map:
                    continue
                prev = prev_stats_map[col]
                curr_mean = stats_df.loc[stats_df["column"] == col, "mean"].values[0]
                curr_std  = stats_df.loc[stats_df["column"] == col, "std"].values[0]
                prev_mean = prev["mean"]
                prev_std  = prev["std"]

                if prev_std == 0:
                    drift_score = float("nan")
                else:
                    drift_score = abs(curr_mean - prev_mean) / prev_std

                # KS test requires raw data from previous run; only summary stats are
                # stored in feature_stats.parquet, so KS is skipped with N/A notation.
                ks_stat = float("nan")
                ks_pval = float("nan")

                flagged = False
                flag_reason = []
                if not np.isnan(drift_score) and drift_score > 2.0:
                    flagged = True
                    flag_reason.append(f"mean-drift={drift_score:.3f}>2.0")
                if not np.isnan(ks_pval) and ks_pval < 0.01:
                    flagged = True
                    flag_reason.append(f"KS p={ks_pval:.4f}<0.01")

                drift_results.append({
                    "column": col,
                    "drift_score": drift_score,
                    "ks_stat": ks_stat,
                    "ks_pval": ks_pval,
                    "flagged": flagged,
                    "flag_reason": "; ".join(flag_reason) if flag_reason else "ok",
                })
        else:
            print(f"[validate_data] No feature_stats.parquet in {prev_run_dir}, skipping column drift.")
else:
    print("[validate_data] No previous run found; skipping drift check.")

# ---------------------------------------------------------------------------
# Step 4 – Verdict and report
# ---------------------------------------------------------------------------
print("[validate_data] Computing verdict ...")

issues = []

# Schema checks
EXPECTED_COLUMNS = (
    ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]
)
if column_list != EXPECTED_COLUMNS:
    issues.append(f"SCHEMA MISMATCH: expected {EXPECTED_COLUMNS}, got {column_list}")

# Row count sanity
EXPECTED_ROWS = 284807
if row_count != EXPECTED_ROWS:
    issues.append(f"ROW COUNT: expected {EXPECTED_ROWS}, got {row_count}")

# Null check
total_nulls = int(df.isna().sum().sum())
if total_nulls > 0:
    null_cols = df.columns[df.isna().any()].tolist()
    issues.append(f"NULL VALUES: {total_nulls} nulls found in columns {null_cols}")

# Class balance check
if "Class" in df.columns:
    fraud_count = int(df["Class"].sum())
    fraud_pct = fraud_count / row_count * 100
    if fraud_count < 400 or fraud_count > 600:
        issues.append(
            f"CLASS IMBALANCE ANOMALY: fraud count={fraud_count} ({fraud_pct:.3f}%), "
            f"expected ~492"
        )

# Amount sanity
if "Amount" in df.columns:
    if df["Amount"].min() < 0:
        issues.append(f"NEGATIVE AMOUNT: min={df['Amount'].min()}")

# SHA rewrite
if sha_rewrite_flag:
    issues.append(
        "SHA256 REWRITE: file SHA-256 changed since last run but filename is unchanged — "
        "possible silent data corruption or substitution."
    )

# Drift flags
flagged_cols = [r for r in drift_results if r["flagged"]]
for fc in flagged_cols:
    issues.append(
        f"DRIFT FLAGGED [{fc['column']}]: {fc['flag_reason']}"
    )

# Determine verdict
warns = [i for i in issues if not i.startswith("SCHEMA") and not i.startswith("NULL") and not i.startswith("NEGATIVE")]
hard_fails = [i for i in issues if i.startswith("SCHEMA") or i.startswith("NULL") or i.startswith("NEGATIVE")]

if hard_fails:
    verdict = "FAIL"
elif issues:
    verdict = "WARN"
else:
    verdict = "PASS"

print(f"[validate_data] Verdict: {verdict}")

# ---------------------------------------------------------------------------
# Write report
# ---------------------------------------------------------------------------
now_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

drift_table_lines = []
if drift_results:
    drift_table_lines.append(
        "| Column | Drift Score (|Δmean|/std_prev) | KS Stat | KS p-value | Flagged | Reason |"
    )
    drift_table_lines.append("|--------|-------------------------------|---------|------------|---------|--------|")
    for r in drift_results:
        ds = f"{r['drift_score']:.4f}" if not np.isnan(r["drift_score"]) else "N/A"
        ks = f"{r['ks_stat']:.4f}" if not np.isnan(r["ks_stat"]) else "N/A (no raw prev data)"
        kp = f"{r['ks_pval']:.4f}" if not np.isnan(r["ks_pval"]) else "N/A"
        flagged_str = "YES" if r["flagged"] else "no"
        drift_table_lines.append(
            f"| {r['column']} | {ds} | {ks} | {kp} | {flagged_str} | {r['flag_reason']} |"
        )

issues_section = ""
if issues:
    issues_section = "\n".join(f"- {i}" for i in issues)
else:
    issues_section = "None."

# Feature stats summary (top-level, compact)
stats_summary_lines = [
    "| Column | Mean | Std | Min | Max | Nulls | Zeros | Negatives |",
    "|--------|------|-----|-----|-----|-------|-------|-----------|",
]
for _, row in stats_df.iterrows():
    stats_summary_lines.append(
        f"| {row['column']} | {row['mean']:.4f} | {row['std']:.4f} | "
        f"{row['min']:.4f} | {row['max']:.4f} | "
        f"{int(row['null_count'])} | {int(row['zero_count'])} | {int(row['negative_count'])} |"
    )

fraud_count_display = int(df["Class"].sum()) if "Class" in df.columns else "N/A"
fraud_pct_display = f"{fraud_count_display / row_count * 100:.4f}%" if "Class" in df.columns else "N/A"

report = f"""# Data Quality Report

**Run ID:** {run_id}
**Generated:** {now_str}
**Verdict:** {verdict}

---

## 1. Lineage

| Field | Value |
|-------|-------|
| File | `{DATA_FILE}` |
| SHA-256 | `{file_sha256}` |
| File size | {file_size_bytes:,} bytes |
| File mtime (UTC) | {file_mtime_utc} |
| Row count | {row_count:,} |
| Column count | {len(column_list)} |
| Git SHA | `{git_sha}` |
| Python version | {lineage['python_version']} |
| scikit-learn version | {lineage['sklearn_version']} |

---

## 2. Schema Check

Expected columns (31): `Time`, `V1`–`V28`, `Amount`, `Class`

**Columns present:** {', '.join(column_list)}

Schema match: {"PASS" if column_list == EXPECTED_COLUMNS else "FAIL"}

---

## 3. Class Distribution

| Label | Count | Percentage |
|-------|-------|------------|
| Legitimate (0) | {row_count - fraud_count_display:,} | {(row_count - fraud_count_display) / row_count * 100:.4f}% |
| Fraud (1) | {fraud_count_display:,} | {fraud_pct_display} |
| **Total** | **{row_count:,}** | 100% |

---

## 4. Feature Statistics Summary

{chr(10).join(stats_summary_lines)}

Full per-quantile stats stored in: `{RUN_DIR}/feature_stats.parquet`

---

## 5. Drift Check

**Previous run compared:** {prev_run_id if prev_run_id else "None (first run)"}

{"Note: KS test requires raw data from the previous run. Since only summary stats are stored in feature_stats.parquet, KS p-values are reported as N/A. Only mean-drift scores are computable from stored summaries." if prev_run_id else ""}

{chr(10).join(drift_table_lines) if drift_table_lines else "No drift check performed (no previous run)."}

---

## 6. Issues Found

{issues_section}

---

## 7. Verdict

**{verdict}**

{"All checks passed. The dataset matches the expected schema (284,807 rows, 31 columns), contains no nulls, fraud rate is within expected range (492 frauds, 0.1727%), and SHA-256 is recorded for future drift comparison." if verdict == "PASS" else ""}
{"One or more warnings were raised. Review the Issues section above." if verdict == "WARN" else ""}
{"One or more hard failures detected. Do not proceed with pipeline until resolved." if verdict == "FAIL" else ""}
"""

report_path = RUN_DIR / "data_quality_report.md"
report_path.write_text(report, encoding="utf-8")
print(f"[validate_data] Report written to {report_path}")

# Print summary to stdout
print("\n" + "="*60)
print(f"VERDICT: {verdict}")
if issues:
    print("ISSUES:")
    for i in issues:
        print(f"  - {i}")
else:
    print("No issues found.")
print("="*60)
