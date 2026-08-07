# Paper Trading Platform — Direction Notes

Planning notes from an early discussion about extending ALTAIR into a
Tickertape-style paper trading / strategy-testing platform. This captures the
decisions made so far — not an implementation, just the agreed direction and
the state of the current backend as of this write-up.

## The idea

A Tickertape-inspired UI on top of ALTAIR, but instead of only ranking
"weakest companies" for research, let a user paper-trade / simulate a
strategy against real tickers to test it before risking real capital.

## Build order (decided)

1. **Now:** keep the frontend integrated inside the existing FastAPI app
   (`templates/`, Jinja2 + Tailwind/Alpine/Chart.js CDN — no separate
   frontend project) and focus on making the **backend analysis engine
   solid first**. A prettier UI on top of a shaky scoring engine isn't worth
   building yet.
2. **Later, at production stage:** split out a dedicated frontend in
   `astro/` (Astro + React components), once the scoring/paper-trading
   backend has stabilized. `astro/` already exists as a scaffold — see
   `astro/README.md` — but stays parked until this stage.

This matches the project's existing stated plan in the root `README.md`
("port the backend to Rust, finish the Astro frontend") — the paper trading
feature follows the same sequencing, just pulled earlier: backend correctness
first, second frontend second.

## Hosting / infra plan

- ₹35,000 in GCP credits, usable through **October 2026** — intended to fund
  build-and-test hosting for this, not a permanent budget.
- Natural fit: **Cloud Run** for the FastAPI backend (scales to zero, cheap
  while idle), and later Cloud Run or Firebase Hosting/Cloud Storage+CDN for
  the Astro frontend once it's built.
- Because the credits are temporary, keep the setup portable — plain Docker
  + Cloud Run, not GCP-proprietary managed services — so a future move off
  GCP (once credits run out) is a redeploy, not a rewrite.
- Google Workspace and Google AI Pro are **separate products** from GCP
  compute credits and don't contribute to hosting — noted here since it came
  up and is easy to conflate.

## Dev workflow

- Day-to-day build/test loop: **GitHub Codespaces**, not a local laptop
  setup — see `docs/CODESPACES_GUIDE.md` for the full walkthrough (create a
  Codespace on the repo, run `python main.py`, open the forwarded port URL
  in a browser). Free tier (60 core-hrs/month), no GCP involvement needed
  for this part.
- Reserve the GCP credits for actually hosting a deployed trial (Cloud Run),
  not for the IDE itself.

## Current backend state (as analyzed)

Before building paper trading on top of it, worth being clear-eyed about
what the existing scoring engine actually does today:

- **Two hardcoded ticker universes** live in
  `src/engine/hunter/DataCollector.py` (`GlobalBilateralCollector`):
  - **Headline universe (40 tickers)** — 20 US mega-caps + 20 India
    large-caps, no sector tagging. This is the *only* universe actually
    scored when you click "Run Full Audit" (`POST /api/v1/audit` →
    `run_headline_audit()`).
  - **Full sector/sub-sector universe (400 slots)** — 10 sectors × 2
    sub-sectors × 10 tickers, per market (BFSI, IT_Service, Infra, Auto,
    Energy_Renewable, Energy_Fossil, Health, Consumer_Tech_Beauty,
    Telecom_Media, Materials_Metals). US side is 200/200 unique; India side
    is 200 slots but only **196 unique** — `BHEL.NS`, `RECLTD.NS`,
    `SJVN.NS`, and `VEDL.NS` are each duplicated into two different sectors,
    and `VEDL.NS` (a metals/mining company) is filed under
    `Consumer_Tech_Beauty/Beauty_D2C`, which looks like a copy-paste error
    rather than a real classification. This universe is never scored in
    bulk — only on-demand, one sub-sector (10 tickers) at a time, from the
    Analytics/Scenario tab.
- **The score itself isn't purely data-derived.** `VulnerabilityRanker`
  (the pipeline behind every API endpoint, writing
  `data/processed/GLOBAL_STRIKE_MAP_2026.csv`) combines 7 real forensic
  formulas (Altman Z-Score, Beneish M-Score, Piotroski F-Score, Sloan Ratio,
  ROIC, EBITDA Leverage, Short Float) with one factor from
  `src/engine/hunter/BailoutMap.py` — a hand-typed dict of "government
  bailout probability" per ticker (e.g. `AAPL: 100`, `ZOMATO.NS: 0`),
  covering only **35 tickers**. Everything else, including most of the live
  40-ticker Headline universe, silently defaults to a flat `30`. That's a
  subjective constant baked into what's otherwise an objective forensic
  score — worth fixing (drop it, or replace with something data-derived)
  before leaning on this engine for real decisions.
- **No persistence layer.** The backend is entirely stateless CSV
  in/CSV out — there's no database. Paper trading needs to hold state
  (a portfolio, cash balance, open positions, order/fill history) across
  requests, which the current architecture has no mechanism for yet. This
  is the first real design gap to close before any paper-trading feature
  work starts, independent of the scoring-engine fixes above.

## Open questions for when this moves from planning to building

- How to fix/replace the `BailoutMap` constant so the score is fully
  data-derived.
- Whether to widen the "live" scored universe beyond the 40-ticker Headline
  set, or keep the two-tier (fast headline / on-demand sector) split.
- Data model for paper trading: portfolio, positions, orders, and where
  that state lives given there's no DB today (SQLite would be the lightest
  addition that fits the current single-process, no-infra style).
- Whether paper trading strategies read directly off ALTAIR's fragility
  score, or need their own separate signal.

None of the above has been implemented yet — this file only records the
direction agreed on so far.
