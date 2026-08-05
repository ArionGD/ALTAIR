import math
import pandas as pd
from fastapi import APIRouter, HTTPException

from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker
from src.engine.scenario.OilShockEngine import OilShockEngine
from src.engine.swing.SwingScanner import scan_ticker, rank_swing_results
from src.engine.swing.TechnicalScore import calculate_technical_score
from src.cache.DailyCache import get_or_compute

router = APIRouter(prefix="/api/v1", tags=["Scenario Analytics"])


def _clean_records(df):
    rows = df.to_dict(orient="records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows


@router.get("/universe")
async def get_universe():
    """Returns market -> sector -> sub_sector -> [tickers], for the Analytics tab's drill-down selectors."""
    collector = GlobalBilateralCollector()
    return collector.get_universe()


@router.get("/rank")
async def rank_filtered(
    market: str,
    sector: str = None,
    sub_sector: str = None,
    ticker: str = None,
    force: bool = False,
):
    """
    Sector Ranker: fetches and scores whatever the market/sector/sub_sector/
    ticker filter resolves to (any of the last three omitted means "all at
    that level" - e.g. sector alone with no sub_sector scores every
    sub-sector in that sector), then returns tickers ranked strongest to
    weakest fundamentally (ascending astra_strike_score - lower vulnerability
    score is fundamentally stronger).

    Cached per-ticker per-calendar-day (see src/cache/DailyCache.py): the
    first request for a ticker on a given day fetches live and caches the
    result; every later request for that same ticker that same day (whether
    via this exact filter or a different one that happens to include it)
    is served from SQLite instead of re-fetching. Pass force=true to bypass
    the cache and recompute regardless of what's cached for today.
    """
    collector = GlobalBilateralCollector()
    if sector and sector not in collector.markets.get(market, {}):
        raise HTTPException(status_code=404, detail=f"Unknown sector: {market}/{sector}")
    if sub_sector and (not sector or sub_sector not in collector.markets.get(market, {}).get(sector, {})):
        raise HTTPException(status_code=404, detail=f"Unknown sub_sector: {market}/{sector}/{sub_sector}")

    targets = collector.resolve_filtered_tickers(market, sector, sub_sector, ticker)
    if not targets:
        return []

    ranker = VulnerabilityRanker()
    results = []
    for t, sec, sub in targets:
        def _compute(t=t, sec=sec, sub=sub):
            row = {"ticker": t, "market": market, "sector": sec, "sub_sector": sub, "pe_ratio": 0}
            fundamental = ranker.calculate_avs_score_v11(row)
            buy_sell_ratio = calculate_technical_score(t, ranker.auditor)["buy_sell_ratio"]
            return {"ticker": t, "market": market, "sector": sec, "sub_sector": sub,
                    **fundamental, "buy_sell_ratio": buy_sell_ratio}

        result, _ = get_or_compute(t, "rank", _compute, force=force)
        results.append(result)

    scored_df = pd.DataFrame(results)
    # Most-fundamentally-strong first (ascending astra_strike_score - lower
    # vulnerability score is stronger), matching the Ranked Report's intent.
    scored_df = scored_df.sort_values(by='astra_strike_score', ascending=True).reset_index(drop=True)
    scored_df.insert(0, 'rank', range(1, len(scored_df) + 1))

    return _clean_records(scored_df)


@router.get("/swing/scan")
async def swing_scan(
    market: str,
    sector: str = None,
    sub_sector: str = None,
    ticker: str = None,
    force: bool = False,
):
    """
    Swing-Trading Scanner: fetches and scores whatever the market/sector/
    sub_sector/ticker filter resolves to (same "all at that level" semantics
    as /rank), combining fundamental strength (astra_strike_score, via
    VulnerabilityRanker) with technical momentum (TechnicalScore, from daily
    OHLCV) into a two-sided verdict:
      - LONG SETUP: fundamentally strong AND technically bullish
      - SHORT SETUP: fundamentally weak AND technically bearish
      - NO SETUP: mismatched or inconclusive signals
    Results are ranked LONG SETUP first, then SHORT SETUP, then NO SETUP -
    see SwingScanner.classify_swing_setup for the exact tie-break ordering.

    Cached per-ticker per-calendar-day, same as /rank (see
    src/cache/DailyCache.py) - pass force=true to bypass and recompute.
    """
    collector = GlobalBilateralCollector()
    if sector and sector not in collector.markets.get(market, {}):
        raise HTTPException(status_code=404, detail=f"Unknown sector: {market}/{sector}")
    if sub_sector and (not sector or sub_sector not in collector.markets.get(market, {}).get(sector, {})):
        raise HTTPException(status_code=404, detail=f"Unknown sub_sector: {market}/{sector}/{sub_sector}")

    targets = collector.resolve_filtered_tickers(market, sector, sub_sector, ticker)
    if not targets:
        return []

    ranker = VulnerabilityRanker()
    results = []
    for t, sec, sub in targets:
        def _compute(t=t, sec=sec, sub=sub):
            row = {"ticker": t, "market": market, "sector": sec, "sub_sector": sub, "pe_ratio": 0}
            return scan_ticker(row, ranker.auditor, ranker)

        result, _ = get_or_compute(t, "swing", _compute, force=force)
        results.append(result)

    rank_swing_results(results)

    # Reuse _clean_records' NaN->None normalization by round-tripping
    # through a DataFrame - results are plain dicts, not a df.
    return _clean_records(pd.DataFrame(results))


@router.get("/scenario/oil")
async def run_oil_scenario(
    market: str,
    sector: str,
    sub_sector: str,
    baseline_price: float = 80.0,
    target_price: float = 100.0,
):
    """
    On-demand scoped oil-price shock scenario: fetches and scores only the
    ~10 tickers in the selected market/sector/sub-sector (live, right now),
    then classifies them by oil-exposure beta x fragility into hard short /
    temporary correction / weak-but-dormant / beneficiary / resilient.

    Scoped deliberately — scoring the full ~400-ticker universe on every
    request would be slow; picking one sub-sector keeps this fast enough to
    run interactively from the Analytics tab.
    """
    collector = GlobalBilateralCollector()
    if sector not in collector.markets.get(market, {}) or sub_sector not in collector.markets.get(market, {}).get(sector, {}):
        raise HTTPException(status_code=404, detail=f"Unknown market/sector/sub_sector: {market}/{sector}/{sub_sector}")

    raw_file = collector.run_scoped_audit(market, sector, sub_sector)

    ranker = VulnerabilityRanker()
    scored_df = ranker.score_scoped(raw_file)

    engine = OilShockEngine()
    result = engine.classify_scored_dataframe(scored_df, baseline_price=baseline_price, target_price=target_price)

    return _clean_records(result)
