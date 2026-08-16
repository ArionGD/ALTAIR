# Gold Master — 20% Enrichment Tier

## Factors added on top of the 10% tier

| Column | Source | What it is |
| :--- | :--- | :--- |
| `inflation_annual_rate` | FRED `CPIAUCSL` | Trailing 12-month US CPI inflation rate (monthly print, forward-filled to daily) |
| `inflation_daily_rate` | Derived | Annual rate converted to a **compounding** daily-equivalent rate |
| `real_gold_return` | Derived | `gold_return - inflation_daily_rate` — the inflation-adjusted (real) daily return |

## Method: proper compounding, not naive division

US inflation is reported as a monthly CPI print; the "annual rate" is
itself a trailing 12-month % change. To apply it against a *daily* gold
return, naive division (`annual_rate / 252`) would under-compound and
drift increasingly wrong across the year. Instead:

```
daily_rate = (1 + annual_rate) ** (1/252) - 1
```

This is exact by construction — 252 compounding days at `daily_rate`
reproduces `annual_rate` precisely. A CPI gap month (this window had one,
around Oct 2025 — likely a reporting delay) is forward-filled within the
monthly series itself before computing the trailing rate, so one missing
print doesn't create a spurious spike.

## Findings

**Sanity check, full 10-year window:**
- Nominal gold return: **+204.23%**
- Inflation-adjusted (real) gold return: **+121.43%**

This large gap (roughly halving the apparent gain) confirms the
compounding logic works as intended — a meaningful fraction of gold's
"headline" 10-year gain was just inflation, not real purchasing-power
appreciation. This tier's factors were not fed into the EGB pattern model
directly (real_gold_return is a *relabeling* of the target, not a new
predictive feature) — its role here is data-quality/framing, feeding
forward into how gold's "true" performance should be read in every later
tier.

## Files

- Raw data: `data/raw/Gold/GOLD_MASTER_20PCT.csv`
- Script: `src/Linear Regression/build_gold_master_20pct.py`
