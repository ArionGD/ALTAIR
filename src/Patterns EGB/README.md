# Patterns EGB — Glass-Box Multi-Factor Pattern Finder

("EGB" = Explainable Gradient Boosting — gradient-boosted trees, e.g.
XGBoost/LightGBM, read with SHAP-value explanations rather than treated
as a black box.)

## What this engine is for

Generalizes `Linear Regression`'s single-factor beta into a **multi-factor**
exposure model: instead of "how much does oil alone explain this stock's
moves," this answers "given oil, the S&P 500, interest rates, and any
other factor at once, which one actually matters most for this ticker,
and by how much."

This is infrastructure, not a single hardcoded answer. The payoff is a
reusable tool: drop in any set of aligned daily time series (any number of
factor columns + one target column) and get back which factors matter and
how much, per ticker — without writing new regression code for every new
pair of series you want to compare (oil vs. stock, rates vs. sector, S&P
500 vs. stock, all at once).

## Why not just run three separate linear regressions instead

Linear regression handles one factor cleanly, but real macro factors are
correlated with each other (oil prices and the S&P 500 both move with
general risk sentiment, for instance). Fit oil and S&P 500 as two
*separate* single-factor regressions and you'll often get misleading betas
for both, because each regression is silently absorbing some of the
other's effect. Gradient-boosted trees handle multiple, correlated inputs
without that confounding, and — critically for this project — SHAP values
let you decompose *why* the model produced a given exposure number for a
given ticker, instead of just trusting a black-box score.

"Glass-box" here specifically means: every output must be explainable back
to which input factor(s) drove it and by how much, in a way a human can
read and sanity-check. A model whose reasoning can't be inspected has no
place in a tool meant to justify short-selling conviction to a person
relying on it.

## How it works (conceptually)

1. **Assemble a feature table**: one row per trading day, columns for each
   factor's daily return (oil, S&P 500, 10Y yield move, etc.) plus the
   target ticker's daily return as the label.
2. **Fit a gradient-boosted tree model** (XGBoost/LightGBM) to predict the
   ticker's return from the factor returns — the model's job is not to
   forecast the future, it's to characterize how the ticker's *historical*
   moves decomposed across the given factors.
3. **Run SHAP** (SHapley Additive exPlanations) over the fitted model to
   get, per factor, an average contribution magnitude — this is the
   "multi-factor beta" output, analogous to Linear Regression's single
   `beta` column but now one row per (ticker, factor) pair instead of one
   number per ticker.
4. **Cross-check against the single-factor linear betas.** If Linear
   Regression said oil beta = 0.7 and this multi-factor model says oil's
   SHAP contribution is near zero once the S&P 500 is also in the mix,
   that's a meaningful finding — it means the earlier oil correlation was
   actually just broad market beta in disguise, not real oil sensitivity.

## Output shape

One row per (ticker, factor): `ticker, factor, shap_importance,
direction, model_r_squared`. Same consumer pattern as Linear
Regression's output — feeds a `ScenarioEngine` that wants per-ticker,
per-factor exposure, but now able to run a scenario that combines
multiple simultaneous shocks (e.g. "oil spikes AND rates rise") without
double-counting overlapping effects.

## Relationship to the other two engines in `src/`

- **`Linear Regression`**: the single-factor baseline this generalizes —
  build and trust that first; this folder's model should agree with it in
  the single-factor case as a basic sanity check before being trusted for
  multi-factor output.
- **`Prediction XGB`**: same underlying model family (gradient boosting)
  but a different *task* — forecasting future returns rather than
  explaining past exposure. Don't conflate the two: this engine is never
  used to predict tomorrow's price, only to explain today's/historical
  sensitivity.
