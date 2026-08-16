import glob
import json
import math
import os
import pandas as pd
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1", tags=["EGB GlassBox"])

# Gold enrichment-tier pattern results. Each tier's *_SUMMARY.json is
# written by src/Patterns EGB/run_gold_patterns*.py (R2, factor importance,
# SHAP-based direction). Findings write-ups live alongside as markdown —
# see data/raw/Gold/md/*.md.
GOLD_DIR = os.path.join("..", "database", "raw", "Gold")
GOLD_MD_DIR = os.path.join(GOLD_DIR, "md")

# Richest available tier's raw daily series — used for the full-width
# multi-factor comparison chart (levels, not the model's _return/_change
# columns, so the chart shows actual price/rate history, not derivatives).
TIMESERIES_FILE = os.path.join(GOLD_DIR, "GOLD_MASTER_40PCT.csv")
TIMESERIES_LEVEL_COLUMNS = {
    "gold_close": "Gold ($)",
    "oil_close": "Oil ($)",
    "fed_funds_rate": "Fed Funds Rate (%)",
    "real_10y_yield": "Real 10Y Yield (%)",
    "dollar_index": "Dollar Index",
}

PERIOD_TO_DAYS = {
    "1W": 7, "1M": 30, "6M": 182, "1Y": 365, "5Y": 365 * 5, "10Y": 365 * 10,
}
MAX_CHART_POINTS = 300  # auto-downsample so long windows (10Y) stay light to render


def _list_tier_summaries():
    pattern = os.path.join(GOLD_DIR, "*_SUMMARY.json")
    files = sorted(glob.glob(pattern))
    tiers = []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            tiers.append(json.load(f))
    return tiers


@router.get("/egb/tiers")
async def list_egb_tiers():
    """Returns every enrichment tier's R2/factor-importance/direction summary, for the EGB GlassBox tab."""
    tiers = _list_tier_summaries()
    if not tiers:
        raise HTTPException(status_code=404, detail="No EGB tier results found — run the Patterns EGB scripts first.")
    return tiers


@router.get("/egb/timeseries")
async def get_egb_timeseries(period: str = "1Y"):
    """
    Returns the raw factor levels (gold, oil, Fed rate, real yield, dollar
    index) over the requested period, each series rebased to % change from
    the period's first value — so scales as different as gold ($1000s) and
    the Fed rate (single-digit %) are visually comparable on one chart,
    the same way ticker-tape / stock-comparison charts normalize series.

    Auto-downsamples to at most MAX_CHART_POINTS so a 10-year daily window
    doesn't ship ~2500 points to the browser for no visual benefit.
    """
    period = period.upper()
    if period not in PERIOD_TO_DAYS:
        raise HTTPException(status_code=400, detail=f"period must be one of {list(PERIOD_TO_DAYS)}")

    if not os.path.exists(TIMESERIES_FILE):
        raise HTTPException(status_code=404, detail="Gold Master time series not found.")

    df = pd.read_csv(TIMESERIES_FILE, parse_dates=["date"])
    cutoff = df["date"].max() - pd.Timedelta(days=PERIOD_TO_DAYS[period])
    df = df[df["date"] >= cutoff].sort_values("date").reset_index(drop=True)

    if df.empty:
        raise HTTPException(status_code=404, detail="No data in the requested period.")

    # Downsample by taking an evenly-spaced slice — preserves the overall
    # shape of the series without needing real resampling/aggregation,
    # which would blur daily volatility that's part of what a ticker-tape
    # chart is meant to show.
    if len(df) > MAX_CHART_POINTS:
        step = math.ceil(len(df) / MAX_CHART_POINTS)
        df = df.iloc[::step].reset_index(drop=True)

    labels = df["date"].dt.strftime("%Y-%m-%d").tolist()
    series = []
    for col, label in TIMESERIES_LEVEL_COLUMNS.items():
        if col not in df.columns:
            continue
        values = df[col]
        base = values.iloc[0]
        if base == 0 or pd.isna(base):
            continue
        pct_change = ((values - base) / abs(base) * 100).round(3)
        series.append({
            "column": col,
            "label": label,
            "values": [None if pd.isna(v) else v for v in pct_change.tolist()],
        })

    return {
        "period": period,
        "labels": labels,
        "series": series,
        "point_count": len(labels),
    }


@router.get("/egb/findings/{tier}")
async def get_egb_findings(tier: str):
    """Returns the markdown findings write-up for one tier (e.g. 'GOLD_30PCT')."""
    filename = f"{tier}_FINDINGS.md"
    path = os.path.join(GOLD_MD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No findings doc for tier '{tier}'.")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"tier": tier, "filename": filename, "content": content}
