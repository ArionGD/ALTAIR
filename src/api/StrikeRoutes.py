import os
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks

# Import ALTAIR Engine Components
from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker
from src.engine.hunter.BailoutAuditor import generate_global_bailout_audit

router = APIRouter(prefix="/api/v1", tags=["Sovereign Audits"])

# Configuration: Path to the Global Strike Maps
DATA_DIR = "data/processed"
MASTER_FILE = "data/processed/GLOBAL_STRIKE_MAP_2026.csv"
V5_FILE = "data/processed/ALTAIR_STRIKE_LIST_V5.csv"

def get_master_data():
    if not os.path.exists(MASTER_FILE):
        return None
    return pd.read_csv(MASTER_FILE)

# Audit State Management
audit_status = {"in_progress": False, "last_run": None}

def run_full_forensic_pipeline():
    """Executes the complete ALTAIR strike chain."""
    global audit_status
    audit_status["in_progress"] = True
    try:
        print("[!] Starting ALTAIR Full Forensic Pipeline...")
        
        # 1. Data Collection
        collector = GlobalBilateralCollector()
        collector.run_global_audit()
        
        # 2. Vulnerability Ranking (AVS Score)
        ranker = VulnerabilityRanker()
        ranker.process_all_sectors()
        
        # 3. Bailout Audit (Strike Score)
        # Note: Bailout auditor should ideally merge with the latest AVS V4.0
        generate_global_bailout_audit()
        
        audit_status["last_run"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[+] ALTAIR Audit {audit_status['last_run']} Complete. V4.0 Strike Map Updated.")
    except Exception as e:
        print(f"[X] ALTAIR Audit Failed: {e}")
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
        
    return df.to_dict(orient="records")

@router.get("/top-targets/{count}")
async def get_top_targets(count: int = 5, market: str = None):
    """Returns the Top N 'Sovereign Sacrifices' ordered by SS_Score."""
    df = get_master_data()
    if df is None:
        raise HTTPException(status_code=404, detail="Global Strike Map not found.")
    
    if market:
        df = df[df['market'].str.upper() == market.upper()]
        
    top_n = df.head(count)
    return top_n.to_dict(orient="records")

@router.get("/forensic-metrics")
async def get_forensic_metrics():
    """Returns the high-detail V5.0 forensic metrics (AVS, Z, Sentiment, PR, Bailout)."""
    if not os.path.exists(V5_FILE):
        raise HTTPException(status_code=404, detail="AVS V5.0 data not found. Run /audit first.")
    df = pd.read_csv(V5_FILE)
    return df.to_dict(orient="records")

@router.get("/forensic-ticker/{ticker_symbol}")
async def get_ticker_forensics(ticker_symbol: str):
    """Returns detailed forensic breakdown for a specific ticker."""
    if not os.path.exists(V5_FILE):
        raise HTTPException(status_code=404, detail="Audit data not yet generated.")
    df = pd.read_csv(V5_FILE)
    ticker_data = df[df['ticker'].str.upper() == ticker_symbol.upper()]
    
    if ticker_data.empty:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_symbol} not found in current audit.")
        
    return ticker_data.to_dict(orient="records")[0]

@router.get("/astro-pulse")
async def get_astro_pulse():
    """Returns the countdown and fracture risk for the April 19, 2026 Reset."""
    target_date = pd.to_datetime("2026-04-19")
    current_date = pd.to_datetime("now")
    days_to_reset = (target_date - current_date).days
    
    return {
        "event": "SMI 9.4 Sovereign Reset",
        "date": "2026-04-19",
        "days_remaining": days_to_reset,
        "fracture_risk": "CRITICAL" if days_to_reset < 30 else "ELEVATED",
        "primary_signals": ["China Bond Exit", "Oil $150 Threshold", "Saturn-Rahu Exact"]
    }

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
        "engine": "ALTAIR V5.0",
        "working_dir": os.getcwd(),
        "data_ready": os.path.exists(V5_FILE) and os.path.exists(MASTER_FILE)
    }
