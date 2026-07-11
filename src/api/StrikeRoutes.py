import math
import os
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks

# Import ALTAIR Engine Components
from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker

router = APIRouter(prefix="/api/v1", tags=["Sovereign Audits"])

# Configuration: Path to the Global Strike Map (single canonical pipeline, V11)
DATA_DIR = "data/processed"
MASTER_FILE = "data/processed/GLOBAL_STRIKE_MAP_2026.csv"

def get_master_data():
    if not os.path.exists(MASTER_FILE):
        return None
    return pd.read_csv(MASTER_FILE)

def _clean_records(df):
    """NaN isn't valid JSON — some tickers legitimately have missing fields
    (e.g. PE ratio for loss-making companies), so scores can come back NaN."""
    rows = df.to_dict(orient="records")
    for row in rows:
        for key, value in row.items():
            if isinstance(value, float) and math.isnan(value):
                row[key] = None
    return rows

# Audit State Management
audit_status = {"in_progress": False, "last_run": None, "error": None}

def run_full_forensic_pipeline():
    """Executes the ALTAIR headline strike chain: collect -> score/rank.

    Scoped to the fixed 40-ticker headline universe (20 US + 20 India large
    caps) so it stays fast — the full 400-ticker sector/sub-sector universe
    is scored on-demand instead, one sub-sector at a time, from the
    Analytics tab (see /api/v1/scenario/oil)."""
    global audit_status
    audit_status["in_progress"] = True
    audit_status["error"] = None
    try:
        print("[!] Starting ALTAIR Headline Audit (V11.0)...")

        # 1. Data Collection (headline universe only)
        collector = GlobalBilateralCollector()
        collector.run_headline_audit()

        # 2. Unified Vulnerability + Valuation Ranking (writes MASTER_FILE)
        ranker = VulnerabilityRanker()
        ranker.process_all_sectors()

        audit_status["last_run"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[+] ALTAIR Audit {audit_status['last_run']} Complete. V11.0 Strike Map Updated.")
    except Exception as e:
        print(f"[X] ALTAIR Audit Failed: {e}")
        audit_status["error"] = str(e)
    finally:
        audit_status["in_progress"] = False

# Define the router instance for export
strike_router = router 

@router.get("/strike-list")
async def get_strike_list(market: str = None):
    """Returns the full Global Strike Map, optionally filtered by market."""
    df = get_master_data()
    if df is None:
        raise HTTPException(status_code=404, detail="Global Strike Map not found.")
    
    if market:
        df = df[df['market'].str.upper() == market.upper()]

    return _clean_records(df)

@router.get("/top-targets/{count}")
async def get_top_targets(count: int = 5, market: str = None):
    """Returns the Top N 'Sovereign Sacrifices' ordered by SS_Score."""
    df = get_master_data()
    if df is None:
        raise HTTPException(status_code=404, detail="Global Strike Map not found.")

    if market:
        df = df[df['market'].str.upper() == market.upper()]

    top_n = df.head(count)
    return _clean_records(top_n)

@router.get("/forensic-metrics")
async def get_forensic_metrics():
    """Returns the full forensic + valuation breakdown (AVS, Z, Beneish, Piotroski, PE, Bailout) for every ticker."""
    df = get_master_data()
    if df is None:
        raise HTTPException(status_code=404, detail="Strike map not found. Run /audit first.")
    return _clean_records(df)

@router.get("/forensic-ticker/{ticker_symbol}")
async def get_ticker_forensics(ticker_symbol: str):
    """Returns detailed forensic breakdown for a specific ticker."""
    df = get_master_data()
    if df is None:
        raise HTTPException(status_code=404, detail="Audit data not yet generated.")
    ticker_data = df[df['ticker'].str.upper() == ticker_symbol.upper()]

    if ticker_data.empty:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_symbol} not found in current audit.")

    return _clean_records(ticker_data)[0]

@router.post("/audit")
async def trigger_audit(background_tasks: BackgroundTasks):
    """Triggers the full Forensic Audit Pipeline as a background task."""
    if audit_status["in_progress"]:
        return {"status": "warning", "message": "An audit is already in progress."}
    
    background_tasks.add_task(run_full_forensic_pipeline)
    return {"status": "success", "message": "ALTAIR Global Audit initiated in background."}

@router.get("/status")
async def get_audit_status():
    """Returns the status of the background audit process."""
    return audit_status

@router.get("/health")
async def health_check():
    """Verifies that the engine and API are operational."""
    return {
        "status": "online",
        "engine": "ALTAIR V11.0",
        "working_dir": os.getcwd(),
        "data_ready": os.path.exists(MASTER_FILE)
    }
