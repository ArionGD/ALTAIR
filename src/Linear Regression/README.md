# Linear Regression — Beta Learner

## What this engine is for

Replaces the hand-typed `OIL_BETA` dict in `src/engine/scenario/OilShockEngine.py`
with a **measured** exposure coefficient per ticker, learned from real
historical price data instead of manual sector-based reasoning.

Today, `OilShockEngine` looks up a ticker's oil-price sensitivity from a
dict I wrote by hand (e.g. `Energy_Fossil/Integrated_Majors: -0.9`). That
number is an economically-reasoned guess, not a measurement. This engine
computes the same kind of number — a beta — but from actual co-movement
between a stock's returns and a factor's returns (oil, S&P 500, interest
rates, etc.) over a real lookback window.

## How it works

1. **Pull daily history**, not point-in-time snapshots. For a given ticker
   and a given factor (e.g. WTI crude oil price), fetch ~2-3 years of daily
   closes via `yfinance.Ticker(...).history(period="3y")`.
2. **Convert prices to daily % returns**, never use raw price levels.
   Two unrelated series that both trend upward over years will look
   "correlated" purely from the trend — returns strip that out and leave
   only the day-to-day co-movement that actually reflects sensitivity.
3. **Fit**: `stock_return = alpha + beta * factor_return + error`
   (ordinary least squares — this is the entire model). `beta` is the
   exposure coefficient: the number ALTAIR currently hardcodes per
   sector/sub-sector, now measured per individual ticker.
4. **Sanity-check the sign and magnitude** before trusting it: an oil
   producer should come out negative (benefits from higher oil), an
   airline/logistics name should come out positive (hurt by higher oil).
   If the regression disagrees badly with basic economic logic, that's a
   signal of a data problem (bad date alignment, wrong instrument, too
   short a window) — not evidence the economics are wrong.

## Why linear regression, and why first

This is deliberately the simplest possible model — one factor in, one
number out, with a hand-checkable output. If a stock's true relationship
to a macro factor can't be seen in a simple linear regression, a more
complex model (XGBoost, neural net) is very unlikely to have found a real
signal either — it's much more likely to be fitting noise. Linear
regression here is a floor of trust, not a limitation to work around.

**Known simplification, accepted deliberately**: a single linear beta
assumes the relationship is constant over the whole lookback window and
purely linear (no threshold effects, no regime changes). That's a real
limitation — but it's the correct one to accept for a first pass, since it
makes the output easy to audit. Moving past it (e.g. rolling betas that
change over time, or nonlinear effects) is future work once this baseline
is trusted.

## Output shape

One row per ticker: `ticker, factor, beta, r_squared, lookback_days`.
`r_squared` matters as much as `beta` — a beta with very low R² means the
factor barely explains the stock's moves at all, and shouldn't be trusted
as a strong exposure signal even if the sign looks plausible.

This CSV is meant to be read by `OilShockEngine` (or a renamed, more
general `ScenarioEngine`) in place of the hardcoded `OIL_BETA` dict — same
consumer, better-sourced number.

## Relationship to the other two engines in `src/`

- **`Patterns EGB`** (glass-box / explainable gradient boosting): the
  natural next step once single-factor linear betas are trusted — handles
  *multiple* factors at once (oil + S&P 500 + rates simultaneously)
  without them confounding each other, and explains which factor mattered
  most for a given ticker.
- **`Prediction XGB`**: a different, harder problem (forecasting future
  returns) rather than explaining past exposure — see that folder's
  README for why it's scoped separately and treated with more caution.
