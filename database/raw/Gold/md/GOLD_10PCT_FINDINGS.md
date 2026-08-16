# Gold Master — 10% Enrichment Tier

## Factors included

| Column | Source | What it is |
| :--- | :--- | :--- |
| `gold_close` / `gold_return` | yfinance `GC=F` | Gold futures daily close / % return |
| `oil_close` / `oil_return` | yfinance `CL=F` | WTI crude futures daily close / % return |
| `fed_funds_rate` | FRED `DFF` | Effective Federal Funds Rate (daily, forward-filled) |

10-year daily history (2016-07-13 to 2026-07-10), 2,511 rows.

## Method

XGBoost regressor (`n_estimators=200, max_depth=3, learning_rate=0.05`)
predicting `gold_return` from `oil_return`, `fed_funds_rate`, and
`fed_funds_change` (the rate's own day-over-day change, added because the
level alone is non-stationary — it trended from 0.4% to over 5% and back
down to 3.6% across the window, so the model needs the *move* as well as
the *level*). Chronological 80/20 train/test split (never randomly
shuffled — that would let the model see the future). Explained with SHAP
values, so every number below is traceable to which factor drove it.

## Findings

**Out-of-sample R² = -0.0167** — essentially zero, slightly negative.
This means the model explains *less* of gold's daily return than simply
predicting the average return every day would. **Oil price and the
nominal Fed funds rate, on their own, do not meaningfully explain gold's
day-to-day moves.**

Factor ranking (by mean |SHAP impact|):
1. `oil_return` (0.0011)
2. `fed_funds_rate` (0.0006)
3. `fed_funds_change` (0.00006 — negligible)

Direction: all three factors showed a *positive* correlation with their
own SHAP contribution — i.e. on days oil was up, or the Fed rate was
higher/rising, the model's (weak) prediction leaned toward gold being up
too. This is a mild "shared risk-sentiment" signal, not a strong causal
oil→gold or rate→gold link.

## Why this is still a useful result

A near-zero/negative R² is not a failed experiment — it's an honest
finding that rules out two commonly-assumed gold drivers as *not* being
the real story, and it correctly predicted the need for the next tier of
factors (see `GOLD_30PCT_FINDINGS.md`).

## Files

- Raw data: `data/raw/Gold/GOLD_MASTER_10PCT.csv`
- Factor importance: `data/raw/Gold/GOLD_PATTERNS_RESULT_10PCT.csv`
- Machine-readable summary: `data/raw/Gold/GOLD_10PCT_SUMMARY.json`
- Script: `src/Linear Regression/build_gold_master.py` (data),
  `src/Patterns EGB/run_gold_patterns.py` (model)
