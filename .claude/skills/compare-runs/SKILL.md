---
name: compare-runs
description: Diff two pipeline runs' metrics and lineage. Use when comparing the effect of a hyperparameter change, detecting silent regressions, or building a model-change log.
---

# compare-runs

Compare metrics between two stamped runs under `outputs/runs/`.

## Invocation

The user will say one of:

- "Compare the last two runs."
- "Compare <run_id_a> vs <run_id_b>."
- "Show me how metrics changed since <run_id>."

## Steps

### 1. List available runs
```bash
python -c "import pathlib; [print(p.name) for p in sorted(pathlib.Path('outputs/runs').iterdir())]"
```

If fewer than 2 runs exist, stop and say so.

### 2. Resolve which two to compare
- "last two" → pick the two most recent (sort by name descending).
- Explicit ids → use them. Fail if either directory doesn't exist.

### 3. Build the diff
Write `scripts/compare_runs.py` that:

- Loads `lineage.json` from both runs — flag if data SHA differs.
- Loads `anomaly_metrics.csv` from both — diff per-metric per-model.
- Loads `supervised_metrics.csv` from both if present.
- Loads `cluster_profile.csv` — diff cluster sizes and fraud rates by cluster id.
- For each row of each metric table, compute absolute and relative change.

### 4. Produce `outputs/compare_<a>_vs_<b>.md`