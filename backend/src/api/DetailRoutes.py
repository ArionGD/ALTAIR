"""
ALTAIR: Ticker Details — full-page single-ticker breakdown.

Deliberately independent of StrikeRoutes.py's /forensic-ticker (that one
reads a hardcoded, currently-stale CSV path — see CLAUDE.md "Known backend
bug" and the graceful fallback already built around it in dashboard.html's
slide-over). This route fetches live instead, the same pattern already used
by /api/v1/rank and /api/v1/swing/scan - no dependency on any precomputed
file, so it can't go stale.
"""
import math
from fastapi import APIRouter, HTTPException

from src.engine.hunter.SovereignAuditor import SovereignAuditor
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker
from src.engine.swing.TechnicalScore import calculate_technical_score
from src.engine.swing.SwingScanner import classify_swing_setup
from src.cache.DailyCache import get_or_compute

router = APIRouter(prefix="/api/v1", tags=["Ticker Details"])

VALID_PERIODS = {"1mo", "6mo", "1y", "5y", "10y"}


def _clean(value):
    """NaN isn't valid JSON - Starlette's response renderer raises ValueError
    ("Out of range float values are not JSON compliant") if any survives to
    the response body. The fundamental/technical sub-dicts nest one level
    deep (e.g. fundamental['z_score'] can be NaN when a generic-formula
    factor fails to compute - see VulnerabilityRanker.py), so this recurses
    into dicts/lists rather than only cleaning the top level."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


@router.get("/ticker/{ticker}")
async def get_ticker_detail(ticker: str, market: str = None, sector: str = None, sub_sector: str = None, force: bool = False):
    """
    Full breakdown for one ticker: fundamental score (sector-aware, via
    VulnerabilityRanker - same router used by /rank, so Banking/Energy/IT
    tickers get their dedicated factors, not the generic formula), technical
    momentum + buy/sell rate (via TechnicalScore, same as /rank and
    /swing/scan), and the combined swing verdict.

    market/sector/sub_sector are optional context (passed by the Ranked
    Report's "View Details" link, which already knows them) - without them,
    scoring falls back to the generic 8-factor formula since the sector
    router needs a sector name to dispatch on.

    Cached per-ticker per-calendar-day, same as /rank and /swing/scan (see
    src/cache/DailyCache.py) - pass force=true to bypass and recompute. Note:
    this means the cached entry reflects whichever market/sector/sub_sector
    context was passed on the FIRST view that day - if the same ticker is
    looked up with different context later the same day, it'll still return
    the first context's cached result until forced or the day rolls over.
    """
    def _compute():
        auditor = SovereignAuditor()
        ranker = VulnerabilityRanker()
        # Reuse one auditor across both calls so the underlying yf.Ticker()
        # is only fetched once, not twice (see SovereignAuditor's cache).
        ranker.auditor = auditor

        row = {
            "ticker": ticker,
            "market": market,
            "sector": sector,
            "sub_sector": sub_sector,
            "pe_ratio": 0,
        }
        fundamental = ranker.calculate_avs_score_v11(row)
        technical = calculate_technical_score(ticker, auditor)
        verdict = classify_swing_setup(fundamental["astra_strike_score"], technical["technical_score"])

        info = auditor.get_ticker_object(ticker).info
        profile = {
            "long_name": info.get("longName"),
            "sector_label": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency"),
        }

        return _clean({
            "ticker": ticker,
            "market": market,
            "sector": sector,
            "sub_sector": sub_sector,
            "profile": profile,
            "fundamental": fundamental,
            "technical": technical,
            "swing_verdict": verdict,
        })

    result, _ = get_or_compute(ticker, "detail", _compute, force=force)
    return result


@router.get("/ticker/{ticker}/history")
async def get_ticker_history(ticker: str, period: str = "1y"):
    """Daily OHLCV for one of the Details page's chart timeframe buttons
    (1mo/6mo/1y/5y/10y). Returns an empty series (not an error) for tickers
    without enough listed history at the requested range - newer listings
    legitimately don't have 10y/5y of data yet."""
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")

    auditor = SovereignAuditor()
    hist = auditor.get_ticker_object(ticker).history(period=period)
    if hist.empty:
        return {"ticker": ticker, "period": period, "candles": []}

    candles = [
        {
            "date": idx.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"]),
        }
        for idx, row in hist.iterrows()
    ]
    return {"ticker": ticker, "period": period, "candles": candles}
