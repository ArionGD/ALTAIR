# ALTAIR — Paper-Trading Sandbox + Free-Tier Hosting Plan

> Status: **planning only** — nothing in this document is implemented yet.
> This plan is scoped to two new asks: (1) make the whole system hostable on
> free-tier infrastructure, and (2) add a "sandbox" that, when the user
> activates the algorithm on a stock, *buys* it (simulated) and displays the
> resulting position.
>
> It sits alongside — and deliberately does not contradict —
> `docs/PLAN_RUST_AXUM_MIGRATION.md` and `astro/PLAN_SAAS_FRONTEND.md`. Where
> those plans and this one touch the same surface (the DB, auth), this plan
> reuses their decisions rather than inventing a parallel one.

## Decisions locked in (from the user)

| Question | Answer | Consequence |
|---|---|---|
| What does "buy" do? | **Paper trading — fully simulated** | No broker account, no API keys, no real money, no regulatory/KYC surface. Positions/cash/P&L are our own DB rows priced off the *existing* live price feed (yfinance, already in the stack). **This is the single biggest enabler of free-tier hosting** — the app stays a read-only-to-the-outside-world service. |
| Which market first? | **US only** | US tickers already flow through the headline universe + `DetailRoutes`/`SovereignAuditor`. No NSE-bridge dependency for v1. India is a later additive step, not a fork. |
| What triggers a buy? | **Manual "Activate" now + optional auto-on-LONG-SETUP later** | v1 = one explicit user click per ticker → one simulated buy. Auto-mode is a phase-2 toggle that reuses the *same* execution path, driven by the Swing Scanner's existing `LONG SETUP` verdict. |

---

## Part A — The Paper-Trading Sandbox

### A.1 What it is (and isn't)

The sandbox is a **virtual brokerage account** living entirely in our own DB.
"Activating the algorithm" on a ticker means: run the existing scoring
(`DetailRoutes`'s live `/ticker/{ticker}` — fundamental + technical + swing
verdict), and if the user confirms (or auto-mode fires on `LONG SETUP`),
record a simulated BUY at the current live price. From then on the position's
market value and unrealized P&L are recomputed from the live price every time
the portfolio is viewed. Nothing leaves the process. It is a **simulator that
reuses ALTAIR's own price data**, not a broker integration.

Explicitly NOT in scope: real orders, broker/demo APIs, margin, options,
shorting with borrow mechanics (a "SHORT SETUP" can be modeled as a simple
inverse P&L position later, but v1 is long-only buys), order books, partial
fills, or intraday tick data (the stack is daily-bar only — see
`TechnicalScore.py`'s docstring on why intraday yfinance is unreliable).

### A.2 Data model (SQLite — reuse the DB the other plans already chose)

Both existing plans already converge on **one SQLite file under `data/`**:
`astro/PLAN_SAAS_FRONTEND.md` proposes `data/altair.db` for auth, and
`src/cache/DailyCache.py` already ships `data/altair_cache.db` and explicitly
notes it should share "one lightweight local DB" posture with that future
auth DB. **The sandbox tables live in that same auth DB** (`data/altair.db`),
not a third file — so identity, sessions, and portfolios are one store.

```
portfolio        one virtual account (v1: one per user; pre-auth: one global "demo")
  id
  user_id        FK -> user (from the SaaS plan); NULL/"demo" until auth lands
  cash_balance   starting virtual cash, e.g. 100_000.00 (USD)
  created_at

position         an open holding (one row per ticker per portfolio)
  id
  portfolio_id   FK
  ticker
  quantity
  avg_cost       cost basis (updated on each add)
  opened_at
  status         OPEN | CLOSED

trade            immutable ledger of every simulated fill (audit trail)
  id
  portfolio_id   FK
  ticker
  side           BUY | SELL
  quantity
  price          live price captured at execution time
  trigger        MANUAL | AUTO_LONG_SETUP    (so we can tell them apart later)
  executed_at
  strike_score   snapshot of astra_strike_score at buy time (for later analysis)
  technical_score snapshot of technical_score at buy time
```

Positions are **derivable** from the `trade` ledger, but a materialized
`position` table keeps the portfolio view a cheap point-read (same reasoning
as `DailyCache` — don't recompute on every page load). The `trade` table is
the source of truth; `position`/`cash_balance` are maintained transactionally
alongside each insert.

### A.3 Pricing — reuse what exists, no new data source

- **Execution price**: `SovereignAuditor.get_ticker_object(t).fast_info`'s
  `lastPrice` — the exact call `MarketRoutes.get_daily_movers` already uses
  for the 40-ticker movers scan. One cheap number per fill.
- **Mark-to-market for the portfolio view**: same `fast_info.lastPrice`,
  fetched per held ticker, wrapped in `DailyCache.get_or_compute` (kind
  `"quote"`) so viewing the portfolio repeatedly in a day costs one real
  fetch per ticker, not one per page load. A `force=true` refresh button
  (same pattern as the movers panel) re-marks live.
- No new dependency, no paid market-data plan, no websocket. This is what
  makes it hostable for free.

### A.4 New backend routes (new `src/api/SandboxRoutes.py`)

```
POST /api/v1/sandbox/activate/{ticker}   Run scoring, execute a simulated BUY.
                                          Body: {quantity, trigger}. Rejects if
                                          cash < price*qty. Returns the new trade
                                          + updated position + cash.
POST /api/v1/sandbox/sell/{ticker}        Close/reduce a position at live price;
                                          realizes P&L into cash_balance.
GET  /api/v1/sandbox/portfolio            Full account: cash, positions (each
                                          marked to live price -> unrealized P&L),
                                          totals. Cached-quote priced (A.3).
GET  /api/v1/sandbox/trades               The trade ledger (history tab).
POST /api/v1/sandbox/reset                Wipe positions/trades, reset cash to the
                                          starting float (so a demo is repeatable).
```

The activate route is intentionally the *only* one that couples to the scoring
engine — it calls the existing `/ticker/{ticker}` compute (via a shared helper
or an internal call to `DetailRoutes`' logic) so the buy decision and the
displayed analysis are the same numbers, then writes the trade. Everything
else is pure portfolio arithmetic over the DB.

### A.5 Auto-mode (phase 2, same execution path)

A per-portfolio `auto_mode` boolean. When on, buys fire automatically on a
`LONG SETUP` from the Swing Scanner instead of requiring a click. Two ways to
drive it, in order of free-tier friendliness:

1. **Lazy / on-view (preferred for free tier):** when the user opens the Swing
   tab (which already calls `/api/v1/swing/scan`), any `LONG SETUP` ticker not
   already held gets auto-activated in the same request cycle. No background
   process, no always-on worker — works on platforms that sleep idle apps.
2. **Scheduled worker (only if a real scheduler is available):** a cron/worker
   re-scans and auto-buys on a timer. Deferred — most free tiers either have no
   always-on worker or sleep the app, making a reliable scheduler the hard
   part. Don't build this until hosting is chosen (Part B) and actually
   supports it.

v1 ships manual only; auto-mode lands after the portfolio + manual path are
verified end-to-end.

### A.6 Frontend — a new dashboard tab (`templates/core/_sandbox.html`)

Follows every rule in `CLAUDE.md`'s dashboard section: standalone `core/`
shell, paired `light`/`dark:` classes, lucide icons covered by
`refreshIcons()`, Chart.js canvases guarded by the `if (rows.length)` +
single-`$watch` pattern already documented there. Adds:
- A sidebar entry "Sandbox" (via `setTab('sandbox')`).
- An **[Activate]** button on Strike List / Swing / Details rows that POSTs to
  `/sandbox/activate/{ticker}` and toasts the fill.
- The Sandbox tab: cash + total-value KPI tiles (reuse `bloc/ui.html`'s
  `stat_tile`), a positions table (live-marked, green/red P&L), an equity-vs-cost
  bar or a simple portfolio-value line chart, and a trades-history sub-table.
- An auto-mode toggle (disabled/"coming soon" until phase 2).

When the Astro SaaS frontend (`astro/PLAN_SAAS_FRONTEND.md`) lands, this same
API backs an Astro `/sandbox` page — the routes are the contract, the
Jinja2 tab is just the first client.

### A.7 Build order for Part A

1. DB tables + a thin `Portfolio` service class (`src/engine/sandbox/`) with
   `buy()`, `sell()`, `mark_to_market()`, `reset()` — pure DB + price logic,
   unit-testable without HTTP. Verify with direct calls before any route.
2. `SandboxRoutes.py` wrapping the service; verify each route with `curl`.
3. `_sandbox.html` tab + Activate buttons; verify by driving the real dashboard
   (`/run` skill) — click Activate, see the position appear and mark live.
4. Auto-mode (lazy/on-view) once 1–3 are solid.

---

## Part B — Free-Tier Hostability

### B.1 The three things that make free-tier hard today, and the fix for each

| Blocker (today) | Why it fights free tier | Fix |
|---|---|---|
| **`data/` is local, gitignored, generated by a multi-minute live scrape** | Free tiers have **ephemeral disks** — anything written at runtime is wiped on restart/redeploy/sleep. A fresh boot would have no strike map and no portfolio. | Portfolios/trades → **hosted managed DB** (see B.3), not a local file. The scraped strike map → either committed as a seed CSV, or regenerated lazily; it's derived data, losing it only costs a re-audit. |
| **Heavy, mostly-unused dependencies** (`xgboost`, `shap`, `scikit-learn`, `alpha_vantage`, `textblob`, `pandas-datareader`) | Free tiers cap build image size / RAM (often 512 MB). `xgboost`+`shap`+`scikit-learn` alone can blow a 512 MB image and slow cold starts. The Rust plan already confirmed **none of these are imported in `src/`**. | Split `requirements.txt`: a lean **`requirements-web.txt`** (`fastapi uvicorn jinja2 pandas numpy yfinance requests python-dotenv`) for the deployed service; keep the ML libs in a separate `requirements-research.txt` used only by the offline `src/Linear Regression/` + `src/Patterns EGB/` scripts, which don't run in the request path. |
| **`POST /audit` scrapes ~40 tickers with `time.sleep(1)` between each** | A multi-minute request will hit free-tier **request timeouts** (often 30–60 s) and may exceed monthly compute-minute caps if run often. | Don't run audits on the free web dyno. Either (a) commit a pre-generated `GLOBAL_STRIKE_MAP_2026.csv` as seed data so the app is useful on first boot with zero scraping, and/or (b) run audits from your own machine / a separate scheduled job and push results to the hosted DB. The interactive routes (`/ticker`, `/rank`, `/swing`, sandbox) are already per-ticker + `DailyCache`-backed, so they stay within timeout. |

### B.2 What's already free-tier-friendly (keep it)

- `DailyCache` (SQLite, lazy, per-day) already makes the live-scoring routes
  cheap and idempotent — exactly the shape free tiers reward.
- The whole app is **one process, no Node build** for the `templates/` path
  (CDN Tailwind/Alpine/Chart.js) — trivial to containerize.
- No websockets, no always-on worker required for v1 (sandbox is
  request-driven; auto-mode's lazy/on-view design keeps it that way).

### B.3 Storage: the one real change needed

Ephemeral disk is the crux. SQLite-on-local-disk (what `DailyCache` and the
planned auth/sandbox DB assume) **does not survive** on most free tiers.
Options, cheapest-effort first:

1. **Managed free Postgres** (e.g. Neon / Supabase free tier) for the
   *stateful* tables only — `user`, `portfolio`, `position`, `trade`. Point
   SQLAlchemy (the ORM `astro/PLAN_SAAS_FRONTEND.md` already picks) at
   `DATABASE_URL`; use SQLite locally, Postgres in prod via the same ORM. The
   `DailyCache` price cache can stay ephemeral SQLite (it's *supposed* to
   expire daily — losing it on restart is harmless, it just re-fetches).
2. **Platform-provided persistent volume** if the chosen host offers one on
   free tier (some do, most don't) — keep SQLite, mount the volume at `data/`.
3. **Litestream-style SQLite replication to object storage** — more moving
   parts; only if 1 and 2 are unavailable.

Recommendation: **option 1**. It cleanly separates "must survive" (a real DB)
from "fine to lose" (the daily price cache), and it's the same DB the SaaS
auth plan needs anyway — so this decision is shared, not sandbox-specific.

### B.4 Candidate hosts (evaluate at implementation time, not committed here)

Backend (FastAPI): a container-based free/hobby tier (Render free web service,
Fly.io free allowance, Railway trial, or similar). Frontend, once Astro lands:
static/SSR on Netlify (already the stated target) or Cloudflare Pages.
DB: Neon/Supabase free Postgres (B.3, option 1). **Cold-start sleep** is the
main free-tier tax — acceptable for a research tool; the sandbox's lazy
pricing tolerates it fine. Pick concrete hosts when Part A is built and there's
a real image to deploy — don't lock a vendor in a planning doc.

### B.5 Interaction with the Rust/Astro plans

- **Rust migration:** unaffected in principle — the sandbox is new routes over
  a DB, and the strangler-fig plan ports routes one at a time. When Rust ports
  the sandbox routes, the portfolio *math* is exactly the kind of pure
  arithmetic that plan says moves cleanly to native Rust; the price *fetch*
  stays a PyO3 Python call. The DB choice (B.3) is language-neutral (Postgres
  over a URL), so it doesn't need re-deciding at port time.
- **SaaS auth:** the sandbox **depends on** the `user`/`portfolio` link from
  `astro/PLAN_SAAS_FRONTEND.md`, but doesn't *require* auth to ship first — v1
  can run against a single global `"demo"` portfolio (no login), then bind
  portfolios to `user_id` once auth lands. Sequencing them the other way
  (auth first) also works; they're not mutually blocking.

---

## Suggested overall order (when the user says go)

1. **B.1/B.3 groundwork** (small, high-leverage): split `requirements.txt`;
   introduce the SQLAlchemy DB abstraction with a `DATABASE_URL` so local
   SQLite and hosted Postgres are the same code. This unblocks both the
   sandbox and the SaaS plan.
2. **Part A, steps 1–3**: portfolio service → `SandboxRoutes` → `_sandbox.html`
   tab + Activate buttons, against a single `"demo"` portfolio (no auth yet).
   Verify end-to-end by driving the real dashboard.
3. **Deploy the lean image** to a chosen free-tier host + free Postgres; prove
   the seed strike map + live pricing + a manual buy all work in prod.
4. **Auto-mode (lazy/on-view)** once the manual path is proven in prod.
5. **Bind to auth** (`user_id` on portfolios) when the SaaS plan's login lands.
6. Update `README.md` / `CLAUDE.md` together to document the sandbox tab and
   the split requirements / DB env var — in the same change as the code, not
   ahead of it.

## Explicit non-goals (for this plan)

- No real-money trading, broker/demo APIs, KYC, or order-routing — ever, under
  this plan; that's a different product with a different risk profile.
- No intraday/tick data, order books, margin, or options.
- No change to the scoring algorithm — the sandbox *consumes* existing scores.
- No India market in v1 (additive later; no NSE-bridge dependency introduced).
- No always-on background worker required for v1 (auto-mode is lazy/on-view).
- No vendor lock-in decided here — concrete host/DB picks happen at deploy time.
