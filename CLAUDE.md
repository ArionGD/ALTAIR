# ALTAIR — Agent Notes

## Current project status (important)

This is a **backend-only** project right now. The FastAPI app in `main.py`
serves the JSON API (`/api/v1/*`), a landing page at `GET /` and a self-
contained analysis dashboard at `GET /dashboard` (Tailwind CDN + Alpine.js CDN
+ Chart.js CDN, server-rendered via Jinja2). Running `python main.py` and
opening `http://127.0.0.1:8001` is the complete local dev loop — one process,
no Node/npm needed.

**Template structure** (`templates/`, Jinja2 inheritance) — **two separate
layout shells, deliberately not shared:**
- `base/` — landing-page-only chrome: `base.html` (master layout, Google
  Fonts Inter/Outfit/Syncopate, lucide icons via CDN, `Alpine.store('theme')`
  for dark mode, obsidian scrollbar CSS, Lenis smooth scroll), `header.html`
  (fixed black/white top navbar — circular badge logo, `font-syncopate`
  spaced-caps wordmark, spaced-caps nav, blue-600 pill CTA, theme toggle),
  `footer.html` (dark gradient footer with a link matrix, a decorative market
  ticker tape, and a system-metrics bar). Only `landing/*.html` extend this.
  **The dashboard does NOT use `base/` at all** — don't add
  `{% extends "base/base.html" %}` to anything under `core/`. The landing
  page's theme store and the dashboard's (`dashboard()`'s `isDark`) are
  separate Alpine mechanisms but share the same `altair-theme` localStorage
  key, so the preference is consistent when navigating between the two.
- `bloc/ui.html` — small reusable components as Jinja2 macros (e.g.
  `stat_tile(label, x_text_expr, icon, gradient, value_class)` — a gradient
  icon-badge stat card), with dual `dark:`-variant classes, used by both areas.
- `landing/home.html`, `features.html`, `support.html` — the `/`, `/features`,
  `/support` routes (see `main.py`). All extend `base/base.html`.
- `core/` — the dashboard's own standalone shell (its own `<html>`/`<head>`,
  Inter font only (no Syncopate/Outfit — those are landing-only), its own
  theme toggle, obsidian scrollbar CSS, lucide icons, fixed sidebar + header
  instead of a top navbar):
  - `dashboard.html` — the full page: theme-init script (avoids flash of wrong
    theme), Tailwind `darkMode:'class'` config, all Alpine state, Chart.js
    chart methods. Includes `_sidebar.html`, `_header.html`, and the active
    tab's partial.
  - `_sidebar.html` — left nav (Overview / Strike List / Past Analysis /
    Guide), calls `setTab('name')`, indigo-600 active-state accent with a
    left rail. This is the **one and only** dashboard panel — there is
    deliberately no separate admin panel or per-role variant.
  - `_header.html` — page title, a ticker search box (client-side filter on
    the Strike List tab only, via `search` + `sortedRows()`), market filter,
    refresh/audit controls, health pill, and the theme toggle button
    (`toggleTheme()`).
  - `_overview.html` / `_strikes.html` / `_archive.html` / `_guide.html` — tab
    contents, included via `<template x-if="activeTab === '...'">`. New
    dashboard tabs go here the same way, plus a sidebar button and Alpine
    state as needed.

**Light/dark theme:** `isDark` in the `dashboard()` Alpine component,
persisted to `localStorage` (`altair-theme`). Toggled via `toggleTheme()` in
`_header.html`. Every dashboard template uses paired Tailwind classes
(`bg-white dark:bg-slate-900`, `text-gray-900 dark:text-white`, etc.) —
when adding new dashboard UI, always pair a light class with a `dark:`
variant, never a bare dark-only color. Chart.js colors are NOT CSS — they're
picked in JS via `chartColors()` (keyed on `isDark`) and charts are
re-rendered on toggle (see `toggleTheme()`).

**Icons are lucide** (`<i data-lucide="...">`, CDN script, `lucide.createIcons()`),
not inline SVGs, across both shells. Static chrome (header/sidebar/footer) only
needs `lucide.createIcons()` called once after Alpine initializes. Content
inside the dashboard's `<template x-if="activeTab === ...">` tabs gets
mounted/unmounted, so any lucide icon inside those tabs would go stale on tab
switch — `dashboard()`'s `refreshIcons()` helper is called after `init()`,
`loadData()`, `setTab()`, and `loadArchiveFile()` to re-scan for new
`data-lucide` elements each time the DOM under those tabs changes. If you add
a new icon inside tab content, make sure it's covered by one of those calls
(or add a new one) — icons added elsewhere without a `refreshIcons()` call
after mounting just won't render.

**Chart.js + Tailwind CDN gotcha (already hit once, don't reintroduce):**
creating a `new Chart(canvas, ...)` before `rows` data has loaded produces an
empty chart that never updates, AND creating it twice in quick succession (once
empty at mount, once again right after data arrives) crashes Chart.js
internally (`Cannot read properties of null` inside its resize/draw pipeline —
a real timing race with Tailwind CDN's async style injection, not a red
herring). The fix in `core/_overview.html`/`core/dashboard.html`: each canvas's
`x-init` renders immediately only `if (rows.length)`, and separately registers
`$watch('rows', () => renderXChart($el))` as the *single* trigger for
re-rendering when data changes — don't add a second manual render call
elsewhere (e.g. in `loadData()`) or the double-fire race comes back. Chart
configs also set `animation: false` and `resizeDelay: 100`, and switching tabs
away from Overview calls `destroyCharts()` (via `setTab()`) before Alpine's
`x-if` removes the canvas, or Chart.js throws on the next tick touching the
now-detached element.

**`astro/` is a separate frontend that is under development and not ready.**
It's a scaffolded, working Astro + TypeScript app, but it is intentionally
*not* the current recommended path. Do not build, run, or debug `astro/`
unless the user explicitly asks for Astro/frontend work — default to the
`templates/` path for anything UI-related. See the root `README.md` "Project
status" section for the full explanation, and `astro/README.md` for its own
"coming soon" note.

The long-term plan (stated by the user): keep iterating on the scoring
algorithm in Python/FastAPI since it's fast to prototype with pandas/yfinance,
then once the algorithm stabilizes, port the backend to Rust (Axum) and finish
the Astro frontend for deployment (e.g. Netlify). This repo is currently in the
Python prototyping phase.

## Standalone — no astrology/macro-timing

This project used to pair its financial scoring with a separate astrology-based
"macro timing" concept (a specific target date, zodiac-driven signals) and a
separate frontend project. **That coupling has been deliberately removed** —
the API and dashboard now only compute financial fragility from tickers'
financials/market data. Do not reintroduce timing/astrology signals,
countdowns, or "fracture risk" concepts into the API or UI unless the user
explicitly asks. `docs/` still contains legacy narrative write-ups referencing
the old concept (kept for historical context) — don't treat them as current
direction or wire anything from them back into the code.

## source/ (new, in progress)

A new module for scraping public sentiment/popularity signals about tickers
(X.com, Google/DDG search results) — named "source" for the data sources it
pulls from, not related to "source code". Not wired into the scoring pipeline
or the API yet — treat it as a standalone, independently-run tool until the
user asks to integrate it. See `source/README.md`.

## Phoenix source material (all now under templates/, not served)

The user's separate "Phoenix" project (a personal portfolio/tax/transactions
Django finance app) was pasted in as raw design/feature material, originally
in a top-level `reference/` folder, then consolidated into `templates/` so
**everything for this project lives under one `templates/` folder** — nothing
UI-related sits outside it any more. The slices already fully mined into live
ALTAIR templates (Phoenix's `core/*` → `templates/base/` + `templates/landing/`;
Phoenix's `user/user_base.html` + `partials/header.html` + `partials/sidebar.html`
+ `user_db.html` → the visual language of `templates/core/`) have since been
deleted outright — they were 100% superseded duplicates, not needed once the
design was lifted. What's left is only the parts of Phoenix that were **not**
yet ported or converted:

- `templates/portfolio/`, `templates/tax/`, `templates/transactions/`,
  `templates/analytics/`, `templates/analysis/`, `templates/user/` (just
  `cagr_calc.html` + `cagr_target.html`) — the parts of Phoenix that were
  **not yet ported or converted**: still raw Django templates (`{% url %}`,
  `{% load static %}`, `user.is_authenticated`, etc.), not Jinja2, not wired
  into `main.py`, not adapted to ALTAIR's data model. They're organized here
  as pending raw material — **do not wire these into routes or convert their
  Django syntax until the user explicitly asks for that conversion**; per
  earlier direction, ALTAIR only has **one** dashboard panel (no separate
  admin/user split, no accounts/auth, no convo/notifications/support-chat),
  so building these out means deciding per-feature what a "no-auth, one-panel"
  version even looks like — that's a design conversation to have first, not
  an assumption to make while just reorganizing files.

## Known backend bug

`/api/v1/forensic-metrics` and `/api/v1/forensic-ticker/{ticker}`
(`src/api/StrikeRoutes.py`) read a hardcoded path,
`data/processed/ALTAIR_STRIKE_LIST_V5.csv`, which the current pipeline never
writes (`VulnerabilityRanker` writes `ALTAIR_STRIKE_LIST_V10.csv` instead). So
those two endpoints always 404, and `/api/v1/health`'s `data_ready` flag is
always `false` — even though `/api/v1/strike-list` works fine (it reads a
different, already-working file, `GLOBAL_STRIKE_MAP_2026.csv`, produced by
`BailoutAuditor.py`'s separate, simpler scoring pass). The two scoring formulas
disagree with each other and haven't been reconciled into one canonical
pipeline. Don't "fix" this by just pointing V5_FILE at V10 without checking
whether the V10 CSV's columns match what those two endpoints expect.

## Logo

`templates/static/image/altair.jpg` is the only logo asset — **the user
explicitly rejected an SVG version** (one was built and wired in at one
point; they asked for it removed and the JPG restored everywhere). Don't
re-introduce an SVG/vector conversion of the logo unless asked again.

## Data

`data/raw/` and `data/processed/` are gitignored — a fresh clone has none of
the CSVs referenced elsewhere in the docs/code. They're generated by
`POST /api/v1/audit` (or the "Run Full Audit" button on the dashboard), which
live-scrapes every ticker and takes a few minutes.

`md/` (NOT gitignored) holds one-off past-analysis CSVs from earlier manual
script runs — heterogeneous schemas, browsable via `src/api/ArchiveRoutes.py`
(`GET /api/v1/archive`, `GET /api/v1/archive/{filename}`) and the dashboard's
Past Analysis tab. If adding a new one-off script, drop its output CSV here
and it's automatically picked up — no code changes needed.
