import os
import sys
import io
import csv
import json
from datetime import datetime
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Ensure parent directory in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from advisor.sectors import get_all_sectors, get_sector_tickers
from advisor.engine import run_advisor_scan
from advisor.precalc_engine import (
    start_precalc_scheduler,
    get_precalculated_data,
    run_full_precalc_cycle,
    get_next_sync_slot,
    SCHEDULE_SLOTS,
    _PRECALC_CACHE,
    get_current_ist
)

app = FastAPI(title="ALTAIR ORION", version="3.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_USER = os.environ.get("AUTH_USER", "Aditya.raj")
AUTH_PASS = os.environ.get("AUTH_PASS", "Aditya@3205#")

@app.on_event("startup")
def on_startup():
    """Initializes the background precalc scheduler and loads snapshot cache."""
    start_precalc_scheduler()

class LoginPayload(BaseModel):
    username: str
    password: str

@app.post("/api/login")
def api_login(payload: LoginPayload):
    user = payload.username.strip()
    pwd = payload.password.strip()
    if user.lower() == AUTH_USER.lower() and pwd == AUTH_PASS:
        return {
            "status": "success",
            "authenticated": True,
            "user": user,
            "role": "Lead Portfolio Advisor",
            "token": "altair-orion-session"
        }
    raise HTTPException(status_code=401, detail="Invalid User ID or Password.")

@app.get("/logo.png")
def get_logo():
    candidate_logos = [
        os.path.join(BASE_DIR, "orion_logo.png"),
        os.path.join(PARENT_DIR, "orion_logo.png"),
        os.path.join(PARENT_DIR, "Altair Logo.png"),
        os.path.join(PARENT_DIR, "Garud_Quant-lab_logo.png")
    ]
    for p in candidate_logos:
        if os.path.exists(p):
            return FileResponse(p)
    return Response(status_code=404)

@app.get("/api/sectors")
def api_get_sectors():
    return {"sectors": get_all_sectors()}

@app.get("/api/scan")
def api_scan_sector(sector: str = Query("Pharma & Healthcare"), include_gann: bool = Query(False)):
    try:
        # Fetch pre-calculated result instantly from cache
        cached_pack = get_precalculated_data(sector_name=sector, include_gann=include_gann)
        data = cached_pack.get("data", {})
        metadata = cached_pack.get("metadata", {})
        
        rankings = data.get("rankings", [])
        long_count = sum(1 for r in rankings if r.get("action_type") == "LONG")
        short_count = sum(1 for r in rankings if r.get("action_type") == "SHORT")
        avg_mos = round(sum(r.get("margin_of_safety_pct", 0) for r in rankings) / max(1, len(rankings)), 1)
        
        top_long = next((r for r in rankings if r.get("action_type") == "LONG"), rankings[0] if rankings else None)
        top_short = next((r for r in reversed(rankings) if r.get("action_type") == "SHORT"), rankings[-1] if rankings else None)
        
        kpis = {
            "avg_margin_of_safety": avg_mos,
            "long_count": long_count,
            "short_count": short_count,
            "total_count": len(rankings),
            "top_long": top_long,
            "top_short": top_short
        }
        
        return {
            "status": "success",
            "app_name": "ORION",
            "cached": cached_pack.get("cached", False),
            "last_sync_ist": metadata.get("last_sync_ist"),
            "next_sync_ist": metadata.get("next_sync_ist") or get_next_sync_slot(),
            "schedule_slots": ["09:00", "11:55", "18:00 (IST) Mon-Fri"],
            "sector": sector,
            "include_gann": include_gann,
            "kpis": kpis,
            "rankings": rankings,
            "charts": data.get("charts", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/engine/status")
def api_engine_status():
    """Reports ALTAIR ENGINE precalculation and scheduler status."""
    now_ist = get_current_ist()
    return {
        "engine": "ALTAIR ENGINE Precalc API",
        "current_time_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "is_trading_day": now_ist.weekday() < 5,
        "schedule_slots": SCHEDULE_SLOTS,
        "next_sync_slot": get_next_sync_slot(),
        "metadata": _PRECALC_CACHE.get("metadata", {}),
        "cached_sectors_count": len(_PRECALC_CACHE.get("sectors", {}))
    }

@app.post("/api/engine/trigger-sync")
def api_trigger_sync(background_tasks: BackgroundTasks):
    """Triggers an immediate background calculation across all 10 sectors."""
    background_tasks.add_task(run_full_precalc_cycle, "Manual API Trigger")
    return {
        "status": "initiated",
        "message": "Full pre-calculation pipeline dispatched across all sectors."
    }

@app.get("/api/export")
def api_export_csv(sector: str = Query("Pharma & Healthcare"), include_gann: bool = Query(False)):
    try:
        cached_pack = get_precalculated_data(sector_name=sector, include_gann=include_gann)
        data = cached_pack.get("data", {})
        rankings = data.get("rankings", [])
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        headers = [
            "Rank", "Symbol", "Ticker", "CMP (INR)", "Action Recommendation", "Type",
            "DCF Intrinsic Value", "Margin of Safety (%)", "PE Ratio", "14D RSI",
            "Immediate Support S1", "Immediate Resistance R1", "Risk/Reward", "52W High Discount"
        ]
        if include_gann:
            headers.append("Gann Proximity Score")
            
        writer.writerow(headers)
        
        for r in rankings:
            row = [
                r.get("rank"), r.get("symbol"), r.get("ticker"), r.get("cmp"),
                r.get("action"), r.get("action_type"), r.get("dcf_intrinsic_value"),
                r.get("margin_of_safety_pct"), r.get("pe_ratio"), r.get("rsi_14"),
                r.get("s1_support"), r.get("r1_resistance"), r.get("risk_reward"),
                r.get("from_52w_high")
            ]
            if include_gann:
                row.append(r.get("gann_score"))
            writer.writerow(row)
            
        csv_content = output.getvalue()
        filename = f"altair_orion_{sector.replace(' ', '_').lower()}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def serve_orion_dashboard():
    template_path = os.path.join(TEMPLATES_DIR, "orion.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    raise HTTPException(status_code=404, detail="ORION template not found")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8085))
    uvicorn.run(app, host="0.0.0.0", port=port)
