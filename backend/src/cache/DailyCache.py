"""
ALTAIR: Daily Analysis Cache (SQLite).

Every route that scores a ticker (Sector Ranker's /rank, Swing Scanner's
/swing/scan, Details' /ticker/{ticker}) used to fetch live from yfinance on
EVERY request, even for a ticker someone already analysed five minutes ago.
This cache makes that lazy and per-day: the first time a ticker is analysed
on a given calendar day, its result is saved here; any later request for
that same ticker on the same day is served from SQLite instead of hitting
the network again. A new calendar day, or an explicit `force=true` query
param on the route, invalidates that ticker's entry and triggers a fresh
computation.

Deliberately lazy, not a startup precompute job: eagerly scoring every
sector on server start would burn yfinance calls (and the per-ticker
rate-limit sleep) on sectors nobody looks at that day. Caching on first
real use means the cost is proportional to what's actually browsed.

One file, data/altair_cache.db - gitignored alongside the rest of data/
(see .gitignore's "data/raw/"/"data/processed/" entries; this file lives
directly under data/ so it inherits the same ignore posture without a new
gitignore line). SQLite chosen over a CSV-based freshness file because this
needs point lookups by (ticker, date) and eventually shares the same "one
lightweight local DB" posture the SaaS-auth plan (astro/PLAN_SAAS_FRONTEND.md)
already proposed for user accounts - one engine, not two, if that lands
later. Kept as its own separate .db file for now (not the same file/tables
as that future auth DB) since the two aren't related yet.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path("data/altair_cache.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ticker_cache (
    cache_key   TEXT NOT NULL,
    cache_date  TEXT NOT NULL,
    kind        TEXT NOT NULL,
    payload     TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (cache_key, cache_date, kind)
);
"""


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def _today():
    return date.today().isoformat()


def get_cached(cache_key, kind):
    """Returns the cached payload (already JSON-decoded) for today's date,
    or None if there's no entry yet (first time this key/kind is requested
    today, or the day rolled over since it was last cached)."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT payload FROM ticker_cache WHERE cache_key = ? AND cache_date = ? AND kind = ?",
            (cache_key, _today(), kind),
        ).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        conn.close()


def set_cached(cache_key, kind, payload):
    """Stores payload (any JSON-serializable dict/list) for today's date,
    overwriting whatever was there before for this key/kind (used both for
    first-time writes and for force-refresh overwrites)."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO ticker_cache (cache_key, cache_date, kind, payload, computed_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (cache_key, _today(), kind, json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()


def get_or_compute(cache_key, kind, compute_fn, force=False):
    """The one function routes actually call: returns today's cached value
    for (cache_key, kind) if present and `force` isn't set, otherwise runs
    compute_fn() (no args - callers close over whatever they need), caches
    its result, and returns that. compute_fn's return value must be JSON-
    serializable (plain dicts/lists/numbers/strings/None - the same shape
    the API routes already return)."""
    if not force:
        cached = get_cached(cache_key, kind)
        if cached is not None:
            return cached, True  # (payload, was_cache_hit)

    result = compute_fn()
    set_cached(cache_key, kind, result)
    return result, False
