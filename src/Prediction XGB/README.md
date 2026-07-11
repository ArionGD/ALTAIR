# Prediction XGB — Return Forecasting (Handle With Care)

## What this engine is for

The hardest and riskiest of the three: using XGBoost to forecast a
stock's **future** return (e.g. next-day direction or magnitude) from
features like oil price, S&P 500, the stock's own recent price history,
and volume — rather than explaining *past* co-movement, which is what
`Linear Regression` and `Patterns EGB` do.

This is a genuinely different problem from the other two engines, and it
deserves a different level of caution before any output from it is
trusted or acted on.

## Why this is scoped separately and treated more cautiously

Daily stock returns are famously close to a random walk — most of the
day-to-day move is noise, not signal. That makes return forecasting
uniquely easy to fool yourself with:

- **Lookahead bias**: accidentally using information that wasn't actually
  available at prediction time. Concretely: US markets close at 4pm ET,
  but oil futures keep trading after that — using "today's" oil close as
  a same-day feature for a same-day stock-return label can leak future
  information into the model without it being obvious from the code.
- **Overfitting to noise**: XGBoost with enough features and enough trees
  will find "patterns" in what is actually random noise. A backtest can
  look excellent and still be worthless out-of-sample, because the model
  memorized the specific noise in the training window rather than a real
  repeatable relationship.
- **Survivorship and regime-change risk**: a model trained on the last
  three years of data implicitly assumes the next period behaves like the
  training period. Macro regime shifts (rate cycles, geopolitical shocks —
  exactly the scenarios ALTAIR cares about) are precisely the moments a
  historically-fit model is most likely to fail.

None of this means forecasting is impossible — professional quant shops
do it — but they spend enormous effort on walk-forward validation (train
only on data before a cutoff, test only on data after it, roll the cutoff
forward repeatedly), transaction-cost-aware backtesting, and explicit
regime-robustness checks. A first-pass model without that rigor is worse
than no model, because it creates false confidence rather than an honest
"we don't know."

## Relationship to ALTAIR's actual goal

ALTAIR's stated goal is finding **fundamentally weak stocks that break
hard under a scenario** — a fragility/exposure question, not a "what will
the price do tomorrow" question. `Linear Regression` and `Patterns EGB`
already serve that goal directly: they explain *why* a stock is exposed to
a shock, which is what you need to size a short thesis. This engine is not
necessary to hit that goal, and should be treated as a separate,
exploratory project rather than a dependency of the fragility-scoring
pipeline.

## If/when this gets built

- Never train and evaluate on the same time window — use a strict,
  chronological train/test split, and prefer rolling/walk-forward
  validation over a single split.
- Report performance against a trivial baseline (e.g. "always predict
  yesterday's direction continues," or a coin flip) — an accuracy number
  with no baseline to compare against is not evidence of anything.
- Treat any output as a hypothesis to investigate, never as a signal to
  act on directly, until it has survived out-of-sample validation across
  more than one time period and market regime.

## Relationship to the other two engines in `src/`

- **`Linear Regression`** / **`Patterns EGB`**: explain past exposure —
  lower-risk, directly useful today, and the recommended place to spend
  effort first.
- This folder: forecasts future returns — higher-risk, exploratory, and
  intentionally kept separate so its (unvalidated) output can never
  silently flow into the fragility/strike scoring that the rest of ALTAIR
  depends on.
