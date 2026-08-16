# Gold Master — 40% Enrichment Tier

## Factor added on top of the 30% tier

| Column | Source | What it is |
| :--- | :--- | :--- |
| `fed_funds_change_90d` | Derived from `fed_funds_rate` | Cumulative Fed rate move over the trailing 90 calendar days (percentage points) |

## Why this factor, and why it's different from what was already there

The 30% tier already had `fed_funds_rate` (the level) — this tier adds the
**cumulative, sustained** rate move, distinct from a single day's change.
The Fed only actually moves rates at ~8 FOMC meetings a year, so any given
day's rate change is almost always zero — a single-day change can't tell
you whether the Fed has been hiking steadily for a quarter or sitting
still. `fed_funds_change_90d` answers that directly: positive during a
hiking cycle, negative during a cutting cycle, near-zero during a hold.
This was added specifically to test the intuition that **sustained rate
hikes reduce demand for non-yielding gold** — separate from the (already
present) real-yield factor, which nets rates against inflation rather
than measuring the nominal rate cycle on its own.

## Method

Same as prior tiers — XGBoost + SHAP, chronological 80/20 split. Full
feature set: `oil_return`, `fed_funds_rate`, `fed_funds_change` (1-day),
`fed_funds_change_90d` (new), `real_10y_yield`, `real_10y_yield_change`,
`dollar_index_return`.

## Findings

**Out-of-sample R² = 0.0865** — down slightly from the 30% tier's
**0.109**. Adding this factor did not improve, and marginally hurt, the
model's out-of-sample fit.

**`fed_funds_change_90d` ranked 5th of 7 factors** (SHAP impact 0.000335)
— a real but minor factor, well behind `real_10y_yield_change` (still #1)
and `dollar_index_return` (still #2), which remain unchanged as the
dominant drivers.

**Direction was the opposite of the hypothesis being tested**: correlation
of **+0.194** (same direction) rather than negative. On average, days
following a period of cumulative rate hikes leaned slightly toward
*positive* gold returns in this model, not negative.

## Why this is still a useful, honest result

This is not a bug — it's a real finding worth sitting with rather than
discarding:

1. **The effect may already be fully captured by `real_10y_yield_change`**,
   which showed a strong, clean **-0.936** correlation (essentially
   unchanged from the 30% tier). Since real yield = nominal rate minus
   inflation, and the model already has that netted-out version as its
   top factor, `fed_funds_change_90d` may simply be adding a redundant,
   noisier restatement of information the model already has — explaining
   both its low importance and the slight R² decline (extra correlated
   features can dilute a tree model's fit rather than help it).

2. **A slight positive correlation is not necessarily wrong** — gold and
   sustained Fed hiking cycles have coincided historically with periods
   of high inflation concern (e.g. 2022-23), where gold rose *despite*
   rate hikes because inflation fear was the stronger force. A 90-day
   window measures "how much the Fed has moved" but not "why" — it can't
   distinguish a hiking cycle happening during high inflation (gold-
   supportive) from one happening during low inflation (gold-negative).

3. **This is a textbook example of why glass-box, SHAP-explained models
   matter for this kind of work**: a black-box model could have just
   silently absorbed this factor with no visibility into whether it
   helped or hurt. Here, the direction check and R² comparison make the
   disappointing result immediately legible instead of hidden.

## Conclusion

The hypothesis "sustained Fed rate hikes reduce gold demand" is **already
represented, and represented more cleanly, by `real_10y_yield_change`**
in the 30% tier. Adding the raw nominal rate-cycle momentum on its own
does not improve the model and may be redundant with — or confounded by —
the inflation dynamics that the real-yield measure already nets out.

## Suggested next step

Rather than adding more Fed-rate-derived columns, the more promising
direction (per the 30% tier's own suggestions) is still VIX and S&P 500 —
factors not yet represented in any form.

## Files

- Raw data: `data/raw/Gold/GOLD_MASTER_40PCT.csv`
- Factor importance: `data/raw/Gold/GOLD_PATTERNS_RESULT_40PCT.csv`
- Machine-readable summary: `data/raw/Gold/GOLD_40PCT_SUMMARY.json`
- Script: `src/Linear Regression/build_gold_master_40pct.py` (data),
  `src/Patterns EGB/run_gold_patterns_40pct.py` (model)
