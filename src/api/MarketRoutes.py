"""
ALTAIR: Overview tab market context - index charts (Nifty/Nasdaq) and daily
top movers (gainers/losers) across the fixed 40-ticker headline universe
(same set used by "Run Full Audit" and the old Top 10 Strike Scores chart -
see DataCollector.HEADLINE_US/HEADLINE_IND). Deliberately scoped to the
headline universe rather than the full ~400-ticker universe: scanning every
sector/category live on every Overview page load would be slow, and the
headline set is already the large-cap universe that's most relevant here.
"""
from fastapi import APIRouter, HTTPException

from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.SovereignAuditor import SovereignAuditor
from src.cache.DailyCache import get_or_compute

router = APIRouter(prefix="/api/v1", tags=["Market Overview"])

INDEX_TICKERS = {"nifty": "^NSEI", "nasdaq": "^IXIC"}
VALID_PERIODS = {"1mo", "3mo", "6mo"}


@router.get("/market/index/{index_name}")
async def get_index_history(index_name: str, period: str = "6mo", force: bool = False):
    """Daily close history for the Overview tab's index charts. index_name
    is 'nifty' or 'nasdaq' (mapped to ^NSEI/^IXIC - real index tickers, not
    the headline-universe stock baskets), period is 1mo/3mo/6mo.

    Cached per (index, period) per calendar day - see src/cache/DailyCache.py.
    The dashboard's header refresh button is the only thing that passes
    force=true; a plain page load/tab revisit always reads the cache instead
    of re-fetching, so browsing the Overview tab repeatedly in one day costs
    one real fetch, not one per visit.
    """
    if index_name not in INDEX_TICKERS:
        raise HTTPException(status_code=404, detail=f"Unknown index: {index_name}. Use one of {list(INDEX_TICKERS)}")
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400, detail=f"period must be one of {sorted(VALID_PERIODS)}")

    def _compute():
        auditor = SovereignAuditor()
        hist = auditor.get_ticker_object(INDEX_TICKERS[index_name]).history(period=period)
        if hist.empty:
            return {"index": index_name, "period": period, "candles": []}
        candles = [
            {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
        ]
        return {"index": index_name, "period": period, "candles": candles}

    result, _ = get_or_compute(f"index:{index_name}:{period}", "market_index", _compute, force=force)
    return result


@router.get("/market/movers")
async def get_daily_movers(force: bool = False):
    """Top gainers/losers (by today's % change vs. previous close) across
    the 40-ticker headline universe (20 US + 20 India large-caps), split by
    market. Uses yfinance's fast_info (lastPrice/previousClose only) rather
    than the full .info dict per ticker - much cheaper for a 40-ticker scan
    that needs just one number per ticker, not the ~160-field info blob.

    Cached once per calendar day (see src/cache/DailyCache.py) - a 40-ticker
    live scan on every Overview visit was the actual cost users noticed,
    not the theoretical worst case. force=true (wired to the dashboard
    header's refresh button) bypasses the cache and rescans live.
    """
    def _compute():
        collector = GlobalBilateralCollector()
        auditor = SovereignAuditor()
        universe = collector.get_headline_universe()

        result = {}
        for market, tickers in universe.items():
            rows = []
            for t in tickers:
                try:
                    fi = auditor.get_ticker_object(t).fast_info
                    last_price = fi.get("lastPrice")
                    prev_close = fi.get("previousClose")
                    if not last_price or not prev_close:
                        continue
                    change_pct = (last_price - prev_close) / prev_close * 100
                    rows.append({
                        "ticker": t,
                        "market": market,
                        "last_price": round(float(last_price), 2),
                        "change_pct": round(float(change_pct), 2),
                    })
                except Exception:
                    continue  # one bad ticker (delisted/rate-limited) shouldn't blank the whole panel

            rows.sort(key=lambda r: r["change_pct"], reverse=True)
            result[market] = {
                "gainers": rows[:10],
                "losers": list(reversed(rows[-10:])) if len(rows) > 10 else list(reversed(rows)),
            }
        return result

    result, _ = get_or_compute("headline_universe", "market_movers", _compute, force=force)
    return result
