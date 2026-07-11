import math
from fastapi import APIRouter, HTTPException

from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker
from src.engine.scenario.OilShockEngine import OilShockEngine

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
