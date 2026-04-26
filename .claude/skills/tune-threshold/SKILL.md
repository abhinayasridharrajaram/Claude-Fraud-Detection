---
name: tune-threshold
description: Find the anomaly-score threshold that matches a business review-capacity constraint, and report the expected fraud capture. Use when the user says "we can review N transactions per day" or asks for threshold tuning.
---

# tune-threshold

Translate a business constraint ("we have analyst capacity to review N
transactions per day") into a concrete score threshold and a projected
fraud-capture rate.

## Invocation

User typically says:

- "Tune the threshold for a capacity of 500 transactions per day."
- "What score cutoff should we use if we can only review 1% of volume?"
- "Give me a threshold for 99% recall."

Parse the constraint into one of these modes:
- **daily_capacity**: N transactions per day → top N / (rows / days_in_window)
- **pct_volume**: top X% of all transactions
- **target_recall**: lowest threshold that captures ≥ X% of positives

## Steps

### 1. Read the inputs
- `outputs/ml/anomaly_scores.parquet` (needs `if_score` and `Class`)
- `outputs/lineage.json` to get the time span in days (the dataset is 2 days;
  if run on a different slice, use what's there).

### 2. Write `ml/03_threshold_tuner.py`
```python
# pseudocode
scores = pd.read_parquet("outputs/ml/anomaly_scores.parquet")
scores = scores.sort_values("if_score", ascending=False)
total_rows = len(scores)
days = 2  # or read from lineage

if mode == "daily_capacity":
    k = capacity * days
elif mode == "pct_volume":
    k = int(total_rows * pct / 100)
elif mode == "target_recall":
    total_fraud = scores["Class"].sum()
    cum_caught = scores["Class"].cumsum()
    k = (cum_caught >= total_fraud * target).idxmax() + 1

threshold = scores.iloc[k - 1]["if_score"]
caught = scores.iloc[:k]["Class"].sum()
total_fraud = scores["Class"].sum()
precision = caught / k
recall = caught / total_fraud
```

### 3. Report

Print and also append to `outputs/threshold_decisions.md`: