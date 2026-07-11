<img src="templates/static/image/altair.jpg" alt="ALTAIR" width="96" />

# ALTAIR: Financial Fragility Engine

ALTAIR identifies "systemically weak" companies (**Glass Pillars**) for short-selling
research by scoring them on solvency, leverage, earnings quality, and other
purely financial/market-data forensic metrics — no astrology, no macro-timing
signals, no external "when to strike" input. Give it a ticker universe, it
scores fragility from financials alone.

## ⚠️ Project status (read this first)

**This is a backend-only project.** Everything you need to run and interact
with ALTAIR locally lives in the FastAPI app — it serves its own Tailwind +
Alpine.js dashboard directly, so you only need **one process running**
(`python main.py`) to see and use it in a browser.

- ✅ **`templates/`** (served at `GET /` and `GET /dashboard`) — the current,
  working local UI: a landing page plus a tabbed analysis dashboard with
  charts. Quick to run, no Node/npm required.
- 🚧 **`astro/`** — a separate Astro + TypeScript frontend, **under
  development, coming soon.** It's scaffolded and functional (see
  `astro/README.md`) but is *not* the recommended path right now — don't spend
  time wiring new features into it or debugging it unless specifically asked.
  Treat it as a future replacement for `templates/dashboard.html` once the
  scoring pipeline itself has stabilized.
- 🧪 **`source/`** — new, in-progress module for scraping public sentiment
  (X.com, Google/DDG search results) about tickers. Not wired into the scoring
  pipeline or the API yet.

If you're an agent picking up this repo cold: **default to the FastAPI +
`templates/` path.** Don't run or modify `astro/` unless the user explicitly
asks for frontend/Astro work.

**This project has no astrology/macro-timing component.** An earlier version
of this codebase paired the scoring engine with an external "timing" concept
(when a macro fracture would happen) and a separate frontend project; that
coupling has been removed. All of that is gone from the running code — the API
only computes financial fragility. `docs/` still contains narrative/strategy
write-ups from that earlier phase (some reference the old timing concept) —
they're kept for historical context only and don't reflect the current
direction or the current code.

---

## Architecture (current)

```
┌────────────────────────────────────────────────────────┐
│  main.py  (FastAPI)                                       │
│  ├─ /api/v1/*    JSON API (StrikeRoutes.py, ArchiveRoutes.py) │
│  ├─ /            Landing page — navbar/footer shell           │
│  │                (templates/landing/home.html, extends base/) │
│  └─ /dashboard    Analysis dashboard — its OWN shell            │
│                    (sidebar + header, templates/core/), does not │
│                    extend the landing page's base/base.html        │
│      Tailwind (CDN, darkMode:'class') + Alpine.js (CDN) + Chart.js │
│      Light/dark theme toggle (persisted in localStorage)            │
│      fetches /api/v1/* same-origin, no CORS needed                    │
└────────────────────────────────────────────────────────┘
        127.0.0.1:8001 — the only thing you need to run
```

The landing page (`/`) and the dashboard (`/dashboard`) intentionally use
**separate layout shells**. The landing page extends `base/base.html` (simple
top navbar + footer, matching a marketing-page feel). The dashboard is its own
standalone template with a sidebar + header (a typical admin-dashboard
layout) and its own theme toggle — it does not extend `base/base.html`.

There's no database — the backend reads/writes plain CSV files under `data/`.

## Repo layout

```
main.py                     FastAPI entrypoint (run this to start the backend)
requirements.txt            Backend Python dependencies
.env                         Backend config (port, log level, API keys)

templates/                  Jinja2 templates (server-rendered HTML)
├── base/                   Landing-page-only chrome (NOT used by the dashboard)
│   ├── base.html            Master layout for the landing page: <head>, header/footer includes
│   ├── header.html          Simple top navbar (Home / Dashboard / Launch Dashboard CTA)
│   └── footer.html          Footer
├── bloc/                    Small reusable components (Jinja2 macros), used by both areas
│   └── ui.html               stat_tile(), panel() — dual light/dark classes
├── landing/                 The home page
│   └── home.html             Hero + feature blurbs + "Launch Dashboard" button, extends base/base.html
└── core/                    The analysis dashboard — its own standalone shell, does NOT
                               extend base/base.html (separate header + sidebar, own theme toggle)
    ├── dashboard.html         Full standalone page: <html>/<head>, theme init script, Alpine
    │                           state + Chart.js chart methods, includes sidebar/header/tabs below
    ├── _sidebar.html          Left nav (Overview / Strike List / Past Analysis / Guide)
    ├── _header.html           Top bar: page title, market filter, refresh/audit controls,
    │                           health pill, theme toggle button
    ├── _overview.html         Overview tab: KPI stat tiles, 2 charts, top-5 target cards
    ├── _strikes.html          Strike List tab: full sortable table
    ├── _archive.html          Past Analysis tab: generic viewer for md/ archive CSVs
    └── _guide.html            Guide tab: beginner-friendly glossary of every score/metric

src/
├── api/
│   ├── StrikeRoutes.py      All JSON API routes (prefix /api/v1)
│   ├── ArchiveRoutes.py     Lists/reads md/ archive CSVs (prefix /api/v1)
│   ├── DashboardRoutes.py   Serves templates/core/dashboard.html at /dashboard
│   └── templates.py         Shared Jinja2Templates(directory="templates") instance
└── engine/
    ├── hunter/             Pipeline: fetch data → score → rank → bailout-adjust
    ├── grade/               Individual scoring formulas (Z-Score, Beneish M-Score,
    │                         Piotroski F-Score, Sloan Ratio, ROIC, EBITDA Leverage,
    │                         Short Float — each a standalone class)
    ├── bridge/              NSEDataBridge — direct nseindia.com scraper for .NS tickers
    └── aladdin/             ScenarioOrchestrator — standalone "what-if" macro
                              scenario simulator (oil price / supply-chain / capital-flow
                              shocks — not wired into the API)

source/                     🧪 New — public sentiment scraping (X.com, Google/DDG),
                              not yet wired into the scoring pipeline (see source/README.md)

data/
├── raw/                    Per-sector raw ticker data (written by the collector)
└── processed/              Ranked output CSVs (read by the API — see "Known issue" below)

scripts/                    Standalone one-off analysis scripts (run manually with
                              `python scripts/<name>.py`), not called by the API
md/                          Output CSVs from past manual script/simulation runs —
                              browsable in the dashboard's Past Analysis tab
astro/                      🚧 Coming soon — future Astro frontend (see astro/README.md)
docs/                       Design notes and strategy write-ups, including legacy
                              narrative from an earlier astrology-linked concept
                              (superseded — see "Project status" above)
```

---

## Running it locally

Just the backend — one terminal, one process.

```powershell
# from the repo root
python -m venv .venv                     # skip if .venv already exists
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open **`http://127.0.0.1:8001`** in a browser — that's the landing page; click
**Launch Dashboard** (or go straight to `/dashboard`) for the analysis view.

Check the raw API is alive too, if you want:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/health"
```

**`data/` is gitignored — a fresh clone has no CSVs at all.** The dashboard's
Overview tab (KPI tiles + charts) and Strike List tab (table) will say "No
data" until you generate some. Click **Run Full Audit** on the dashboard (or
`POST /api/v1/audit` directly) — it fetches every ticker live (yfinance / NSE
scrape) with rate-limit delays between calls, so the first run can take
several minutes. The dashboard polls `/api/v1/status` and refreshes
automatically when it's done. After that, `data/raw/` and `data/processed/`
are populated locally and subsequent loads are instant.

The dashboard has its own sidebar (left) + header (top) — a separate layout
from the landing page's simple navbar. Sidebar tabs: **Overview** (KPI stat
tiles, a top-10 strike score chart, an average-strike-score-by-sector chart,
and the top-5 target cards), **Strike List** (the full sortable table — click
a card or row to open a ticker detail panel), **Past Analysis** (browse older
one-off CSVs saved under `md/` — simulations, manual scans, earlier
strike-list versions; historical snapshots, not live data, each with its own
columns since different scripts produced them), and **Guide** (a plain-English
glossary of every score/column, for someone with zero background in the
underlying forensic-accounting metrics). The market filter dropdown in the
header applies across all tabs. The header also has a **theme toggle**
(sun/moon button) — light/dark preference is saved in `localStorage` and
persists across reloads.

### Astro frontend (optional, not required)

`astro/` is a separate, more polished frontend that's still under
construction — see `astro/README.md` if you want to poke at it, but it's not
needed to use ALTAIR locally today.

---

## API reference

All endpoints are versioned under `/api/v1` on port 8001.

| Method | Path | What it does |
| :--- | :--- | :--- |
| GET | `/health` | Engine status + whether processed data exists |
| GET | `/strike-list?market=US\|IND` | Full ranked strike map |
| GET | `/top-targets/{count}?market=...` | Top N rows by strike score |
| GET | `/forensic-metrics` | Deep forensic breakdown for all tickers *(see known issue)* |
| GET | `/forensic-ticker/{ticker}` | Deep forensic breakdown for one ticker *(see known issue)* |
| POST | `/audit` | Runs the full fetch → score → rank pipeline in the background |
| GET | `/status` | Whether a background audit is currently running |
| GET | `/archive` | Lists past-analysis CSV filenames under `md/` |
| GET | `/archive/{filename}` | Returns one archived CSV as JSON (columns + rows, any schema) |

Non-API HTML pages: `GET /` (landing page), `GET /dashboard` (analysis dashboard).

## Known backend issue (worth fixing before relying on it)

`/forensic-metrics` and `/forensic-ticker/{ticker}` read a hardcoded path,
`data/processed/ALTAIR_STRIKE_LIST_V5.csv`, but the current ranking pipeline
(`VulnerabilityRanker.process_all_sectors()`) writes `ALTAIR_STRIKE_LIST_V10.csv`
instead. That file has never existed in this repo, so those two endpoints
currently 404 and `/health`'s `data_ready` flag is always `false`, even though
`/strike-list` works fine (it reads a different file,
`GLOBAL_STRIKE_MAP_2026.csv`, produced by a separate, simpler scoring pass in
`BailoutAuditor.py`). The dashboard is written defensively around this — it
falls back to the strike-list row if the forensic-ticker call fails — but the
two scoring formulas disagree with each other and should be reconciled into one
canonical pipeline at some point.

---

## Where this is headed

The plan: keep iterating on the scoring algorithm here in Python (fast to
experiment with pandas/yfinance) using the `templates/` dashboard for local
testing, and layer in the `source/` module as a new signal once it's built
out. Once the algorithm is stable, port the backend to Rust (Axum) for a
lighter, faster service that's easier to run on free-tier hosting, and finish
the Astro frontend (`astro/`) for a proper deployed UI (e.g. on Netlify). This
repo is the prototyping phase of that plan.
