# Gold Master — 30% Enrichment Tier

## Factors added on top of the 20% tier

| Column | Source | What it is |
| :--- | :--- | :--- |
| `real_10y_yield` / `real_10y_yield_change` | FRED `DFII10` | 10-Year TIPS (inflation-protected) yield, level and day-over-day change |
| `dollar_index` / `dollar_index_return` | FRED `DTWEXBGS` | Trade-weighted US Dollar Index, level and % return |

## Why these two factors specifically

Gold pays no interest or dividend, so its opportunity cost is the **real**
(inflation-adjusted) yield available on a safe asset — not the nominal
rate, and not inflation alone, but the two netted together. The 10-Year
TIPS yield is the standard, direct measure of that opportunity cost, and
is widely considered gold's single strongest conventional explanatory
factor.

Gold is also priced in USD globally — a stronger dollar mechanically
makes gold more expensive for non-US buyers, dampening demand regardless
of anything happening in the US economy directly. The trade-weighted
Dollar Index is the standard measure of that effect.

## Findings

**Out-of-sample R² = 0.109** (6 factors) — up from **-0.0167** (3 factors,
10% tier). Going from "explains nothing" to genuinely capturing ~11% of
gold's daily return variance out-of-sample is a substantial, meaningful
jump for daily financial data.

**Factor ranking flipped entirely** vs. the 10% tier:

1. `dollar_index_return` (0.00247) — now the #1 factor
2. `real_10y_yield_change` (0.00212) — #2
3. `real_10y_yield` (0.00059)
4. `oil_return` (0.00058) — dropped from #1 to #4
5. `fed_funds_rate` (0.00021)
6. `fed_funds_change` (0.00003)

**Direction — both new factors match textbook gold theory almost exactly:**
- `dollar_index_return`: correlation **-0.958** with its own SHAP
  contribution — a near-perfect inverse relationship. Stronger dollar →
  weaker gold.
- `real_10y_yield_change`: correlation **-0.942** — rising real yields →
  gold falls, exactly as the opportunity-cost theory predicts.
- `oil_return`: now a secondary, partially-redundant signal (+0.487,
  down from being the dominant factor in the 10% tier) — it was likely
  picking up a fraction of the same broad risk-sentiment move that the
  dollar and real yields capture directly.

## Conclusion

**Gold's real drivers are dollar strength and real interest rates — not
oil prices or the nominal Fed funds rate.** The 10% tier's top factor
(oil) was a weak proxy for signal the 30% tier's factors capture far more
directly. This matches how gold is understood professionally: real
yields and the dollar are the two dominant conventional drivers.

## Known data caveat

`dollar_index` (FRED `DTWEXBGS`) had a publication lag at the time this
tier was built — the last several rows of the window show a flat,
forward-filled value rather than fresh daily data. Worth re-running once
FRED catches up before trusting the very latest days' SHAP behavior
specifically; the historical relationship itself (the -0.958 correlation)
is unaffected since it's measured across the full 10-year window.

## Suggested next factors (not yet built)

- **VIX** (`^VIX` via yfinance) — volatility/fear gauge, often drives
  safe-haven gold buying independent of rates/dollar.
- **S&P 500 returns** (`^GSPC`) — broad risk-on/risk-off flows.
- Central-bank gold demand / ETF flow data — genuinely moves the physical
  market but harder to source as a clean free daily series.

## Files

- Raw data: `data/raw/Gold/GOLD_MASTER_30PCT.csv`
- Factor importance: `data/raw/Gold/GOLD_PATTERNS_RESULT_30PCT.csv`
- Machine-readable summary: `data/raw/Gold/GOLD_30PCT_SUMMARY.json`
- Script: `src/Linear Regression/build_gold_master_30pct.py` (data),
  `src/Patterns EGB/run_gold_patterns_30pct.py` (model)
