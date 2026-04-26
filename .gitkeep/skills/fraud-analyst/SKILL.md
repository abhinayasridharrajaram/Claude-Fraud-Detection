---
name: fraud-analyst
description: End-to-end unsupervised fraud detection with audit controls. Routes between data validation, EDA, anomaly detection, clustering, supervised comparison, and final reporting.
---

# fraud-analyst

You are the entry point. Figure out what the user wants and dispatch.

## Step 0 — Stamp the run

Generate `run_id = datetime.now().strftime("%Y-%m-%d_%H%M")`. Create
`outputs/runs/<run_id>/` and write `<run_id>` to `outputs/runs/current_run_id.txt`.
All sub-agents read that file to know where to put their stamped outputs.

## Step 1 — Data validation (always run first)

Invoke `data-validator`. If it returns verdict FAIL, stop and surface the
reasons. If WARN, proceed but mention the warnings in the final summary.

## Step 2 — Route

Ask the user once (skip if clear from their message):

> "What do you want to run?
> **A)** EDA only.
> **B)** Unsupervised ML only.
> **C)** Full unsupervised pipeline (EDA + ML).
> **D)** Full pipeline **+ supervised baseline comparison**."

Dispatch:
- **A** → `eda-analyst` → stop.
- **B** → `ml-analyst` → `insight-writer`.
- **C** → `eda-analyst` → `ml-analyst` → `insight-writer`.
- **D** → `eda-analyst` → `ml-analyst` → `supervised-baseline` → `insight-writer`.

## Step 3 — Stamp outputs into the run directory

After each sub-agent returns, copy its key outputs into
`outputs/runs/<run_id>/` while keeping the `outputs/<name>.md` "latest"
files intact. Files to stamp:

- `outputs/eda_summary.md`
- `outputs/ml_summary.md`
- `outputs/ml_supervised_comparison.md` (if option D)
- `outputs/ml/anomaly_metrics.csv`
- `outputs/ml/supervised_metrics.csv` (if option D)
- `outputs/ml/cluster_profile.csv`
- `outputs/report.md`

## Step 4 — Final summary

Print:
- Run ID.
- Data quality verdict.
- One headline number from each stage.
- Paths to the key output files.
- If multiple runs now exist, suggest: "Run `compare-runs` to diff against
  the previous run."