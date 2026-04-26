# claude-fraud-detection

Unsupervised ML pipeline on the Kaggle Credit Card Fraud dataset, driven by
Claude Code agents.

## Setup

1. Install Python dependencies:

```powershell
   python -m pip install --user duckdb pandas scikit-learn umap-learn matplotlib pyarrow
```

2. Download the dataset:
   - Go to https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud (free signup).
   - Download `creditcardfraud.zip`, unzip, and place `creditcard.csv` at
     `data/creditcard.csv`.
   - Verify: `python -c "import duckdb; print(duckdb.connect().execute(\"SELECT COUNT(*) FROM 'data/creditcard.csv'\").fetchone())"` should print `(284807,)`.

3. Launch Claude Code from the project root:

```powershell
   cd C:\Users\Abhi\claude-fraud-detection
   claude
```

4. In the chat, say: **"Run the fraud-analyst skill end to end."**

## What the agents do

- `eda-analyst` — profiles the dataset (fraud rate, Amount distribution, time patterns, feature correlations). Writes SQL to `sql/` and a summary to `outputs/eda_summary.md`.
- `ml-analyst` — builds anomaly-detection and clustering pipelines, saves scores, cluster profiles, and plots to `outputs/ml/`, narrative to `outputs/ml_summary.md`.
- `insight-writer` — merges both summaries into `outputs/report.md`.


---------------------------------------------------------------------------------
The complete sequence of prompts that produced this project, from empty
folder to polished portfolio writeup. Each prompt is exactly what was typed
into the Claude Code chat window — copy-paste runnable.
Prerequisites (no Claude needed)
Before any prompts run, do this in PowerShell from the project root:
powershell# Create folder structure
cd C:\Users\Abhi\claude-fraud-detection
New-Item -ItemType Directory -Force -Path data, outputs, sql, ml, scripts | Out-Null

# Install Python dependencies
python -m pip install --user duckdb pandas scikit-learn umap-learn matplotlib pyarrow xgboost

# Download the dataset manually from
#   https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
# and place creditcard.csv at data/creditcard.csv

# Verify the data
python download_data.py
# Expected output: [x] data/creditcard.csv OK — 284,807 rows.
Then drop in the project files (CLAUDE.md, .claude/skills/, .claude/agents/,
settings.json, settings.local.json) and launch Claude:
powershellclaude

Prompt 1 — Sanity check (optional, ~10 seconds)
Confirms agents and skills are loaded correctly before you spend tokens on
a real run.
/agents
You should see five agents listed: data-validator, eda-analyst,
ml-analyst, supervised-baseline, insight-writer.
/doctor
Confirms Claude Code is healthy in this folder.

Prompt 2 — The main event (~30 minutes, the only prompt that matters)
This single prompt runs the entire pipeline: data validation, exploratory
analysis, unsupervised ML, supervised baseline, and the polished writeup.
Run the fraud-analyst skill, option D. Full pipeline with supervised baseline comparison.
What happens behind the scenes:

fraud-analyst skill generates a timestamped run_id.
data-validator agent hashes data/creditcard.csv, captures lineage,
verifies the row count.
eda-analyst agent profiles the data, writes 8 SQL queries, produces
outputs/eda_summary.md.
ml-analyst agent builds the feature matrix, trains Isolation Forest,
LOF, and One-Class SVM, runs k-means clustering, produces
outputs/ml_summary.md and all plots.
supervised-baseline agent trains Logistic Regression and XGBoost,
produces outputs/ml_supervised_comparison.md.
insight-writer agent stitches everything into outputs/report.md.

Expected outputs:

outputs/report.md — portfolio writeup
outputs/eda_summary.md
outputs/ml_summary.md
outputs/ml_supervised_comparison.md
outputs/ml/anomaly_scores.parquet
outputs/ml/anomaly_metrics.csv
outputs/ml/cluster_profile.csv
outputs/ml/clusters_umap.png
outputs/ml/fraud_overlay_umap.png
outputs/ml/anomaly_pr_curves.png
outputs/ml/supervised_metrics.csv
outputs/runs/<timestamp>/ — immutable stamped copy of all the above

Expected runtime: 25-35 minutes on a typical laptop.

Prompt 3 — Build the portfolio deck (optional, ~5 minutes)
Turns the report into a 5-slide PowerPoint suitable for an interview or
stakeholder presentation.
Do NOT invoke the fraud-analyst skill. Invoke ONLY the interview-deck skill. Build outputs/Fraud_Detection_Deck.pptx from the existing files in outputs/ — do not re-run EDA or ML. Pull numbers from outputs/ml/anomaly_metrics.csv and outputs/ml/supervised_metrics.csv. Embed outputs/ml/anomaly_pr_curves.png on the results slide and outputs/ml/fraud_overlay_umap.png on the clustering slide. Lead the takeaway slide with "96.8% of supervised ROC-AUC, zero labels used."
The first sentence ("Do NOT invoke the fraud-analyst skill") is important —
without it Claude may default to the top-level skill and re-run the whole
pipeline.

Prompt 4 — Translate metrics into a business decision (optional)
Given a real-world capacity constraint, find the score threshold and
expected fraud capture.
Use the tune-threshold skill. Review capacity is 500 transactions per day.
Produces outputs/threshold_decisions.md with the cutoff IF score, expected
fraud captured, and projected analyst workload. Append-only — every threshold
decision is logged.
Variations:
Use the tune-threshold skill with mode pct_volume and target 1%.
Use the tune-threshold skill — find the threshold that captures 90% recall.

Prompt 5 — Diff two runs (optional, requires ≥2 stamped runs)
After running the pipeline a second time (e.g., with different
hyperparameters), compare the two runs.
To create a second run with a tweaked hyperparameter:
Rerun fraud-analyst option B (ML only). Set Isolation Forest contamination to 0.001 instead of 0.002.
Then diff:
Use the compare-runs skill to compare the last two runs.
Produces outputs/compare_<run_a>_vs_<run_b>.md showing which metrics moved
and by how much. Useful for hyperparameter tuning, regression testing, and
documenting model evolution.

Prompt 6 — Independent review (optional, recommended before publishing)
Have a fresh agent critique the report end-to-end, looking for unsupported
claims, missing caveats, or methodological holes.
Read outputs/report.md, outputs/ml_summary.md, and outputs/ml_supervised_comparison.md. Critique them as a skeptical senior data scientist would. List the three weakest claims, the three most important caveats that are missing, and any place where a number does not appear to be supported by the underlying CSV files in outputs/ml/. Write your critique to outputs/peer_review.md.
This catches inflated claims, missing caveats, and any lingering
hallucinations before the work goes out the door.

Cost estimate
Total Claude API usage for the full sequence (Prompts 1-6) is roughly
$8 to $15 at standard Claude Code subscription rates, or 30-60 minutes
of cumulative tool-call time. Subsequent re-runs are typically cheaper
because the data validator can short-circuit when the lineage hash is
unchanged.

Notes on prompting style

Be explicit about what NOT to do when invoking sub-skills (see Prompt 3).
Claude's router will default to the top-level skill if you do not exclude it.
Cite output file paths in prompts so the agent knows where to read from
and write to. "Build the deck from outputs/ml/anomaly_metrics.csv" is more
reliable than "Build the deck from the metrics."
Anchor headline numbers in the prompt itself when you have a specific
claim to lead with. "Lead with 96.8% of supervised ROC-AUC" produces a
better deck than letting the agent pick its own framing.
Run the cheap prompts first. /agents and /doctor cost essentially
nothing and catch configuration bugs that would otherwise waste a
20-minute run.