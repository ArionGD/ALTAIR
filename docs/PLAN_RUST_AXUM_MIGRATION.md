# ALTAIR — FastAPI → Rust (Axum) + PyO3 Migration Plan

> Status: **planning only** — nothing in this document is implemented yet.
> No `Cargo.toml`, no `.rs` files, no `pyo3` dependency exist in the repo as
> of this writing (confirmed by search). This plan describes how to start
> safely, not a finished design.

## Goal

Move the web server / request-handling layer to Rust (Axum) for speed and
memory safety, while keeping Python for what it's genuinely needed for:
external data fetching (yfinance, NSE scraping, DDGS search) and anything
that leans on a Python-only library. Raw numerical scoring — the actual
fragility-score arithmetic — moves to native Rust. Python stays reachable
from Rust via **PyO3**, called only where Python-only capability is required.

The current stack (`main.py`, FastAPI, uvicorn) keeps running unmodified
throughout this migration — this is a strangler-fig migration, not a
rewrite-and-cutover. Nothing about `/dashboard`, `templates/`, or the
existing `/api/v1/*` contract changes for end users until a route is
deliberately swapped, verified, and only then decommissioned on the Python
side.

## What the codebase actually looks like today (baseline, from investigation)

- **`main.py`** is thin: 5 routers mounted (`StrikeRoutes`, `DashboardRoutes`,
  `ArchiveRoutes`, `ScenarioRoutes`, `EGBRoutes`) + 3 Jinja2 page routes.
  Good sign — the HTTP layer itself has little logic to re-derive in Rust;
  most of it is routing to Python functions.
- **Only two routes do real computation**: `POST /api/v1/audit` (triggers
  the full `VulnerabilityRanker` scoring pipeline as a background task) and
  `GET /api/v1/scenario/oil` (live-fetches ~10 tickers, scores them
  synchronously). Every other route (`strike-list`, `top-targets`,
  `forensic-*`, `archive*`, `egb/*`) just reads a CSV/JSON file off disk and
  returns it — no computation to port, just I/O.
- **The scoring core** (`src/engine/hunter/VulnerabilityRanker.py`,
  `calculate_avs_score_v11`) is **pure scalar arithmetic** — 8 weighted
  financial-ratio factors combined into one score, no numpy/pandas
  vectorization (it's a per-row Python loop), no ML libraries (no xgboost,
  no sklearn, no shap actually used despite being in `requirements.txt`).
  This is exactly the shape of code that ports cleanly to Rust: no
  dynamic-language dependency once the inputs are plain numbers.
- **The catch**: today, each per-ticker factor engine (`ZScore.py`,
  `BeneishMScore.py`, etc. under `src/engine/grade/`) calls the network
  itself mid-computation (via `SovereignAuditor`/yfinance/NSE bridge). The
  "pure math" and "impure fetch" are currently tangled together inside the
  same call path — that tangle has to be pulled apart *before* any of the
  math can move to Rust, independent of what language it ends up in.
- **The I/O layer that must stay Python**: `NSEDataBridge.py` (raw
  `requests` scraping of nseindia.com with cookie/session refresh
  workarounds), `yfinance` itself, and `source/`'s `ddgs`-based search — none
  of these have a mature Rust equivalent, and reimplementing NSE's scraping
  workarounds in Rust would be pure risk for zero benefit.
- **Two competing scorers write the same output file**
  (`data/processed/GLOBAL_STRIKE_MAP_2026.csv`): `VulnerabilityRanker`
  (current, richer, 8-factor) and `BailoutAuditor.py` (older, cruder,
  2-input formula). They aren't simultaneously "disagreeing" — whichever
  runs last wins — but only one should be ported. `VulnerabilityRanker` is
  the actively-wired one and the better candidate; `BailoutAuditor.py`'s
  liveness should be confirmed (likely dead) before touching it at all.

## Why PyO3 (not a full rewrite, not a separate microservice)

Three ways to combine Rust and Python were considered:

1. **PyO3, Rust-hosts-Python** (chosen) — an Axum binary embeds a Python
   interpreter and calls specific Python functions (data fetch, scraping)
   as library calls. Rust owns the process, the HTTP layer, and the routing;
   Python is a subroutine.
2. Separate Python microservice called over HTTP from Axum — rejected for
   now: adds a network hop and a second deployable for logic that's really
   just "fetch this ticker's financials," not a separate bounded service.
3. Full Rust rewrite of the fetch/scrape layer (no Python at all) — rejected:
   `yfinance`, the NSE scraping workarounds, and `ddgs` are exactly the kind
   of brittle, frequently-adjusted, ecosystem-dependent code where Python's
   library maturity is a real advantage; reimplementing them in Rust is
   effort spent on parity, not on anything new.

PyO3 keeps the current Python fetch code (largely) as-is, callable from Rust,
while giving the HTTP layer and the scoring math a native-speed, memory-safe
home.

## Migration phases (strangler-fig — each phase ships independently)

### Phase 0 — Decouple fetch from compute (Python-only, no Rust yet)

Before any Rust exists, refactor `src/engine/grade/*.py` and
`VulnerabilityRanker.py` so each factor engine becomes a **pure function of
already-fetched data** (plain floats/dicts in, a score out), with all
network calls collected upstream into one "gather all raw financials for
this ticker" step. This is required groundwork regardless of Rust — right
now the math and the network I/O are inseparable, and nothing can be ported
piecemeal until they're not. Verify this refactor only by confirming
`GLOBAL_STRIKE_MAP_2026.csv` output is byte-for-byte (or numerically)
identical before/after, on a fixed input snapshot.

### Phase 1 — Stand up a minimal Axum skeleton, in parallel, port nothing yet

Add `Cargo.toml` / a Rust workspace alongside the Python app (e.g.
`rust/` or `axum-gateway/` at repo root — not inside `src/`, to avoid
colliding with Python's `src/`). Get a trivial Axum server running on a
different port, with PyO3 wired up to call one harmless Python function
(e.g. `GET /api/v1/health`'s equivalent) as a smoke test. No production
traffic touches it yet. Goal: prove the toolchain (PyO3 build, Python
interpreter embedding, Windows dev-environment compatibility) works at all,
cheaply, before committing further.

### Phase 2 — Port the thin, no-compute routes first

Move `archive*`, `egb/*`, `forensic-*`, `strike-list`, `top-targets` to
Axum. These just read a file and serve JSON — no PyO3 call needed at all for
most of them (plain Rust file I/O + `serde_json`), making them the lowest-
risk, highest-confidence first port. Run Axum and FastAPI side by side
(different ports, or Axum as a reverse-proxy in front of FastAPI for
not-yet-ported routes) so the cutover is per-route, not all-or-nothing.
Verify each ported route against the FastAPI original with the same request
against the same data snapshot before removing the Python route.

### Phase 3 — Port the pure-arithmetic scoring core to native Rust

Once Phase 0's decoupling exists, `calculate_avs_score_v11` and the
`src/engine/grade/*` factor formulas translate directly into Rust structs/
functions — plain arithmetic, no PyO3 needed for the math itself. The
"gather raw financials" step (yfinance/NSE/requests) stays a Python function
called via PyO3 from Rust; Rust receives the fetched data as a struct/dict
and does all scoring math natively. Verify by running both the Python
scorer and the Rust scorer on the same fetched-data snapshot and diffing
`astra_strike_score` (and each intermediate factor) for every ticker in the
universe — not just spot checks, since this is the number the whole product
is built on.

### Phase 4 — Port `POST /api/v1/audit` and `GET /api/v1/scenario/oil`

These are the two routes that orchestrate fetch (Python, via PyO3) +
score (Rust, native) + write (Rust). By this point both halves already
exist independently from Phases 2-3; this phase is wiring, not new logic.
Keep the background-task semantics of `/audit` (it's long-running/scrapes
the whole universe) — Axum's async runtime (Tokio) handles this natively.

### Phase 5 — Decommission the Python HTTP layer

Only once every route is ported and verified: remove `main.py`'s FastAPI
app and uvicorn entrypoint, leaving Python installed only as an embedded
interpreter for the fetch functions PyO3 calls. `requirements.txt` shrinks
to just what the fetch layer needs (`yfinance`, `requests`, `ddgs`) — the
already-unused `pandas-datareader`, `alpha_vantage`, `textblob`,
`xgboost`/`shap`/`scikit-learn` (confirmed not imported anywhere in `src/`
today) can be dropped at this point if they're still unused, rather than
carried forward speculatively.

## Safety principles across every phase

- **Never break the working FastAPI app while porting.** Each phase adds to
  or runs alongside the existing Python app; nothing is deleted until its
  Rust replacement is verified against real output.
- **Verify with data, not code review, for anything touching the score.**
  The scoring formula is the product — a silent numeric drift (rounding,
  operator precedence, float vs. decimal) would be worse than a crash. Diff
  full CSV output between old and new for every phase that touches
  `calculate_avs_score_v11` or its inputs.
- **Confirm `BailoutAuditor.py` is dead before porting anything scoring-
  related** — don't port two competing formulas; pick the one actually
  wired to `/audit` (`VulnerabilityRanker`) and treat the other as legacy
  unless the user says otherwise.
- **Don't reimplement NSE scraping or `ddgs` search in Rust.** These are
  exactly the fragile, frequently-broken, ecosystem-dependent integrations
  Python is good at; PyO3 exists precisely so this code doesn't need a
  native rewrite.
- **This plan does not touch `astro/`, the SaaS auth plan
  (`astro/PLAN_SAAS_FRONTEND.md`), or `templates/`.** Those are separate,
  independently-sequenced efforts; this document is scoped to the API/engine
  backend only. Whichever lands first, the other should assume the backend
  contract (`/api/v1/*` request/response shapes) doesn't change until its
  own Phase 5 decommission step, so the two efforts don't block each other.

## Explicit non-goals (for now)

- No decision yet on which crates beyond `axum`/`tokio`/`pyo3`/`serde` are
  needed — deferred to Phase 1, once the skeleton is actually being built.
- No change to `data/` or `md/` file formats/locations — the CSV-based
  "database" stays exactly as-is; this migration is only about what process
  reads/writes/serves it.
- No attempt to port `source/`'s sentiment module — it's already unwired
  from the API per current project status, and its search-client is a
  `ddgs`-only integration with no Rust upside.
- No timeline commitment — this plan sequences the *order* of safe steps,
  not a schedule.
