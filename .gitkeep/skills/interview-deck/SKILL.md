---
name: interview-deck
description: Generate a 5-slide portfolio PPTX from outputs/report.md and outputs/ml/*. Use when preparing for an interview walkthrough or stakeholder presentation.
---

# interview-deck

Produce `outputs/Fraud_Detection_Deck.pptx` — a tight 5-slide deck you can
walk an interviewer through in 5 minutes.

## Prerequisite

Invoke the `pptx` skill from `.claude/skills/` before starting. Read its
SKILL.md to get the current best-practice template.

## Slide outline

1. **Title**
   - "Unsupervised Fraud Detection on the Kaggle Credit Card Dataset"
   - Subtitle: "Anomaly detection + clustering, 0 labels in training"
   - Your name, date.

2. **The problem** (one visual + 3 bullets)
   - 284,807 transactions, 0.17% fraud. Labels are unavailable at inference time.
   - Pull the class-imbalance number from `outputs/eda_summary.md`.
   - Use one simple chart: a bar showing 99.83% legit vs 0.17% fraud.

3. **Approach** (diagram + bullets)
   - Feature engineering: log1p(Amount), hour_of_day, PCA features.
   - Models: Isolation Forest, LOF, One-Class SVM (ensemble scoring).
   - Evaluation: precision@top-k vs held-out Class label.
   - Produce a simple left-to-right arrow diagram: Data → Features → Ensemble → Score.

4. **Results** (metrics table + 1 plot)
   - Pull the anomaly metrics table from `outputs/ml/anomaly_metrics.csv`
     and insert as a PPTX table. Highlight the best cell in bold.
   - Embed `outputs/ml/anomaly_pr_curves.png` to the right of the table.

5. **Takeaway + what's next** (bulleted)
   - Headline number: precision@0.1% with lift claim.
   - 3 "what's next" bullets: supervised comparison (link to
     `ml_supervised_comparison.md` if present), production monitoring with
     drift detection (link to `data_quality_report.md`), threshold tuning for
     real capacity (link to `threshold_decisions.md`).

## Style rules

- 28–32 pt headings, 16–18 pt body.
- Consistent color palette: one accent color (deep blue #1F3A68), neutral gray
  text, red only for the fraud/warning category.
- No more than 5 bullets per slide.
- Every number cites its source file in 9pt gray text at the bottom of the slide.