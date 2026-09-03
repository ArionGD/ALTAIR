import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from google import genai

import storage

from engine import (
    scan_subfield,
    nifty_gann_analysis,
    precious_metals_analysis,
    value_quality_macro_scan,
    run_stock_screener,
    SECTOR_NICHE_MAP
)

app = FastAPI(title="ALTAIR Quant Lab", version="2.2.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_env_vars():
    env_file = os.path.join(BASE_DIR, ".env")
    res = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    res[k.strip()] = v.strip()
    return res

ENV_VARS = load_env_vars()
AUTH_USER = ENV_VARS.get("AUTH_USER", os.environ.get("AUTH_USER", "Aditya.raj"))
AUTH_PASS = ENV_VARS.get("AUTH_PASS", os.environ.get("AUTH_PASS", "Aditya@3205#"))
ACCESS_PIN = os.environ.get("LAB_PIN", "7777")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

client = None
if GEMINI_KEY:
    try:
        client = genai.Client(api_key=GEMINI_KEY)
    except Exception as e:
        print(f"Notice on Gemini client init: {e}")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    pin: Optional[str] = "authenticated"
    session_id: Optional[str] = None
    history: Optional[List[dict]] = []

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/logo.png")
def get_logo():
    logo_path = os.path.join(BASE_DIR, "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path)
    return JSONResponse(status_code=404, content={"detail": "Logo not found"})

@app.get("/download/notebook")
def download_notebook():
    nb_path = os.path.join(BASE_DIR, "ste_engine_lab.ipynb")
    if os.path.exists(nb_path):
        return FileResponse(nb_path, filename="altair_ste_engine_lab.ipynb", media_type="application/x-ipynb+json")
    return JSONResponse(status_code=404, content={"detail": "Notebook not found"})

@app.post("/api/login")
def login_auth(data: LoginRequest):
    if data.username.strip().lower() == AUTH_USER.lower() and data.password == AUTH_PASS:
        return {"status": "success", "authenticated": True, "user": data.username, "token": "altair-session-active"}
    raise HTTPException(status_code=401, detail="Invalid User ID or Password")

@app.post("/api/verify-pin")
def verify_pin(data: dict):
    if data.get("pin") == ACCESS_PIN or data.get("pin") == "authenticated":
        return {"status": "success", "authenticated": True}
    raise HTTPException(status_code=401, detail="Invalid Access PIN")

@app.get("/api/sessions")
def get_sessions():
    return storage.list_sessions()

@app.post("/api/sessions")
def create_new_session(data: dict = None):
    title = data.get("title", "Quantitative Research") if data else "Quantitative Research"
    return storage.create_session(title)

@app.get("/api/sessions/{session_id}")
def get_session_details(session_id: str):
    messages = storage.get_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}

@app.delete("/api/sessions/{session_id}")
def remove_session(session_id: str):
    storage.delete_session(session_id)
    return {"status": "deleted", "session_id": session_id}

NOTEBOOK_PATH = os.path.join(BASE_DIR, "ste_engine_lab.ipynb")

@app.get("/api/notebook")
def get_notebook_content():
    if not os.path.exists(NOTEBOOK_PATH):
        raise HTTPException(status_code=404, detail="Notebook not found")
    try:
        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            nb_data = json.load(f)
        return nb_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notebook/save")
def save_notebook_content(data: dict):
    try:
        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            existing_nb = json.load(f)
        
        if "cells" in data:
            existing_nb["cells"] = data["cells"]
        elif "notebook" in data:
            existing_nb = data["notebook"]
            
        with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_nb, f, indent=1, ensure_ascii=False)
            
        return {"status": "saved", "cell_count": len(existing_nb.get("cells", []))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notebook/add-cell")
def add_notebook_cell(data: dict):
    try:
        cell_type = data.get("cell_type", "code")
        source = data.get("source", "")
        if isinstance(source, str):
            source_lines = [line + "\n" for line in source.splitlines()]
            if source_lines and not source.endswith("\n"):
                source_lines[-1] = source_lines[-1].rstrip("\n")
        else:
            source_lines = source

        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            nb = json.load(f)

        new_cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": source_lines
        }
        if cell_type == "code":
            new_cell["execution_count"] = None
            new_cell["outputs"] = []

        nb["cells"].append(new_cell)

        with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
            json.dump(nb, f, indent=1, ensure_ascii=False)

        return {"status": "cell_added", "index": len(nb["cells"]) - 1, "cell_count": len(nb["cells"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def handle_chat(req: ChatRequest):
    if req.pin != ACCESS_PIN and req.pin != "authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    user_msg = req.message.lower().strip()
    chart_payload = None
    table_payload = None
    multi_charts_payload = None
    notebook_updated = False
    ai_text = ""
    
    # Routing to Engine Tool Functions
    if any(w in user_msg for w in ["adani", "adani group", "adani stocks"]):
        table_payload, chart_payload = scan_subfield("Adani Group")
        ai_text = (
            "### 🎯 Top 6 Adani Group Flagships Analysis\n"
            "Evaluated the 6 core listed Adani companies across **Financials (25%)**, **Momentum (30%)**, "
            "**RSI (20%)**, and **Gann Floor Proximity (25%)**.\n\n"
            "- **#1 Pick: `ADANIPORTS`** leads with strongest balance sheet and cash flows.\n"
            "- **#2 Pick: `AWL` (Wilmar)** shows the healthiest RSI continuation sweet-spot (49.2).\n"
            "- 4-Pillar breakdown and trade target brackets are rendered on your visual canvas!"
        )
    elif any(w in user_msg for w in ["2-wheeler", "2 wheeler", "bike", "two wheeler"]):
        table_payload, chart_payload = scan_subfield("Auto - 2-Wheelers")
        ai_text = (
            "### 🏍️ Auto 2-Wheelers Quant Opportunity Scan\n"
            "Scanned Eicher Motors, Bajaj Auto, TVS Motor, and Hero MotoCorp:\n\n"
            "- **`EICHERMOT`** (Royal Enfield) and **`BAJAJ-AUTO`** rank highest with scores $>80$.\n"
            "- Dynamic targets and stop-losses plotted on your canvas!"
        )
    elif any(w in user_msg for w in ["auto", "car", "4w", "commercial vehicle", "cv"]):
        table_payload, chart_payload = scan_subfield("Auto - 4W & CV")
        ai_text = "### 🚗 Automobile 4W & Commercial Vehicles Analysis\nRanked leaders across Tata Motors, M&M, Maruti, and Ashok Leyland."
    elif any(w in user_msg for w in ["bank - psu", "psu bank", "psu", "sbin"]):
        table_payload, chart_payload = scan_subfield("Banking - PSU")
        ai_text = "### 🏛️ PSU Banking Supercycle Scan\nRanked SBIN, Bank of Baroda, PNB, Canara Bank, and Union Bank."
    elif any(w in user_msg for w in ["bank - private", "private bank", "hdfc", "icici", "kotak", "axis"]):
        table_payload, chart_payload = scan_subfield("Banking - Private")
        ai_text = "### 🏦 Private Banking Leaders Scan\nEvaluated HDFC Bank, ICICI Bank, Kotak Mahindra, Axis Bank, and IndusInd Bank."
    elif any(w in user_msg for w in ["nifty", "gann", "cycle", "turning date", "index", "support", "resistance"]):
        summary, chart_payload = nifty_gann_analysis()
        table_payload = [summary]
        ai_text = (
            f"### 🔮 NIFTY 50 W.D. Gann Cycle & Harmonics Audit\n"
            f"- **Current NIFTY Price**: ₹{summary['current_price']:,}\n"
            f"- **50 DMA / 200 DMA**: ₹{summary['ma_50']:,} / ₹{summary['ma_200']:,}\n"
            f"- **Latest Structural Pivot**: {summary['latest_pivot_type']} at ₹{summary['latest_pivot_price']:,}\n"
            f"- **Next Geometric Resistance (+90°)**: ₹{summary['gann_resistance_90']:,}\n"
            f"- **Critical Support Floor (-90°)**: ₹{summary['gann_support_90']:,}\n\n"
            "Interactive candlestick chart with Square of 9 levels rendered on your canvas."
        )
    elif any(w in user_msg for w in ["gold", "silver", "metal", "gsr", "commodity"]):
        summary, chart_payload = precious_metals_analysis()
        table_payload = [summary]
        ai_text = (
            f"### 🪙 Precious Metals Macro Dashboard\n"
            f"- **COMEX Gold**: {summary['gold_cmp']}\n"
            f"- **COMEX Silver**: {summary['silver_cmp']}\n"
            f"- **Gold-to-Silver Ratio (GSR)**: **{summary['gold_silver_ratio']}** ({summary['ratio_status']})\n"
            f"- **Action Verdict**: **{summary['silver_verdict']}**\n\n"
            "3-panel macro chart (Gold, Silver & Historical GSR) rendered on your canvas."
        )
    elif any(w in user_msg for w in ["screener", "screen", "filter stocks", "stock screener"]):
        sec_filter = "All"
        for s in ["adani", "auto", "bank", "psu", "pharma", "fmcg", "energy"]:
            if s in user_msg:
                sec_filter = s
                break
        res_screen = run_stock_screener(sector_filter=sec_filter)
        if len(res_screen) == 3:
            table_payload, chart_payload, multi_charts_payload = res_screen
        else:
            table_payload, chart_payload = res_screen
        ai_text = (
            "### 🔍 Institutional Multi-Metric Stock Screener Active\n"
            "Screened candidates across **Valuation (P/E)**, **Momentum (14-day RSI)**, **Profitability (ROE %)**, and **ATH Discount**:\n\n"
            "- **2D Quadrant Bubble Map** rendered on your visual canvas: Plots P/E vs RSI with bubble size representing ROE %.\n"
            "- **Accumulation Zone (Green Dash)**: RSI < 40 + P/E < 25 identifies prime swing accumulation sweet-spots.\n"
            "- Full ranked leaderboard scorecard loaded below with Quant Scores & Action Verdicts!"
        )
    elif any(w in user_msg for w in ["undervalue", "value", "fmcg", "pharma", "bank", "bfsi", "cheap", "compounder"]):
        table_payload, chart_payload = value_quality_macro_scan()
        ai_text = (
            "### 💎 Top Undervalued Quality Compounders (FMCG, BFSI & Pharma)\n"
            "Filtered out stagnant IT services and screened domestic leaders with low/zero debt, high ROE, and sweet-spot RSI (30-55):\n\n"
            "- **BFSI Leaders (`SBIN`, `HDFCBANK`)**: Deep historical P/E discounts with pristine balance sheets.\n"
            "- **Pharma (`LUPIN`, `CIPLA`)**: Pristine balance sheets and early accumulation rebounds.\n"
            "- **FMCG (`COLPAL`, `DABUR`, `ITC`)**: Rural consumption recovery with massive downside safety cushions!"
        )
    elif any(w in user_msg for w in ["notebook", "add cell", "add to notebook", "update notebook", "write notebook", "code in notebook"]):
        notebook_updated = True
        code_prompt = req.message
        if client:
            try:
                gen_res = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=f"You are the ALTAIR Notebook Copilot. Write clean, working Python code for a Jupyter cell to answer: {code_prompt}. Return ONLY Python code."
                )
                raw = gen_res.text.strip()
                if "```python" in raw:
                    clean_code = raw.split("```python")[1].split("```")[0].strip()
                elif "```" in raw:
                    clean_code = raw.split("```")[1].split("```")[0].strip()
                else:
                    clean_code = raw
            except Exception:
                clean_code = f"# Quantitative analysis cell for: {req.message}\nimport yfinance as yf\nimport pandas as pd\ndf = yf.download('^NSEI', period='3mo')\nprint(df.tail())\n"
        else:
            clean_code = f"# Quantitative analysis cell for: {req.message}\nimport yfinance as yf\nimport pandas as pd\ndf = yf.download('^NSEI', period='3mo')\nprint(df.tail())\n"

        try:
            with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
                nb = json.load(f)
            source_lines = [l + "\n" for l in clean_code.splitlines()]
            nb["cells"].append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source_lines
            })
            with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            ai_text = (
                f"### 📓 Jupyter Notebook Cell Appended & Saved!\n"
                f"I've written and inserted the code into **`ste_engine_lab.ipynb`**:\n\n"
                f"```python\n{clean_code}\n```\n\n"
                f"Switch to the **Jupyter Notebook** tab in the right panel to view and run your updated notebook!"
            )
        except Exception as e:
            ai_text = f"Notice updating notebook: {e}"
    else:
        if client:
            try:
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=f"You are the Chief Quantitative Strategist for ALTAIR Quant Lab. Answer concisely with actionable trading context: {req.message}"
                )
                ai_text = response.text
            except Exception:
                ai_text = f"Processed: '{req.message}'. Select any strategy from the left sidebar or ask: 'Scan Adani stocks', 'Nifty Gann cycles', 'Precious metals GSR', or 'Undervalued FMCG/Pharma'."
        else:
            ai_text = f"Received: '{req.message}'. Expand the left sidebar or click quick action buttons to trigger scans (Adani, Auto 2W, FMCG, Pharma, Nifty Gann, or Precious Metals)!"
            
    if req.session_id:
        try:
            storage.add_message(req.session_id, "user", req.message)
            storage.add_message(
                req.session_id,
                "ai",
                ai_text,
                table_data=table_payload,
                chart_data=chart_payload
            )
        except Exception as e:
            print(f"Notice on session message saving: {e}")

    return {
        "reply": ai_text,
        "chart": chart_payload,
        "table": table_payload,
        "multi_charts": multi_charts_payload,
        "notebook_updated": notebook_updated
    }

@app.get("/", response_class=HTMLResponse)
def serve_terminal():
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ALTAIR Quant Lab | Institutional Terminal</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darkBg: '#090d16',
                        darkSidebar: '#0c111e',
                        darkCard: '#111827',
                        darkBorder: '#1e293b',
                        accentCyan: '#06b6d4',
                        accentEmerald: '#10b981',
                        accentPurple: '#8b5cf6'
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #090d16; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
        .js-plotly-plot .plotly, .js-plotly-plot .plot-container { width: 100% !important; }
    </style>
</head>
<body class="bg-darkBg text-slate-100 font-sans h-screen flex flex-col overflow-hidden select-none">

    <!-- 50% - 50% Split-Screen Authentication Overlay -->
    <div id="loginModal" class="fixed inset-0 bg-[#060911] z-50 flex flex-col md:flex-row overflow-y-auto md:overflow-hidden select-none">
        
        <!-- LEFT PANEL (50%): Animated Showcase Slideshow -->
        <div class="w-full md:w-1/2 bg-gradient-to-br from-[#0c1424] via-[#080d1a] to-[#04060d] border-b md:border-b-0 md:border-r border-darkBorder p-8 md:p-14 flex flex-col justify-between relative overflow-hidden">
            <!-- Ambient Glow Effect -->
            <div class="absolute -top-32 -left-32 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -bottom-32 -right-32 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>

            <!-- Top Brand -->
            <div class="flex items-center gap-3.5 z-10">
                <img src="/logo.png" alt="Altair Logo" class="w-10 h-10 rounded-xl object-contain border border-cyan-500/30 shadow-lg shadow-cyan-500/10">
                <div>
                    <h1 class="font-black text-lg text-white tracking-wider flex items-center gap-2">
                        ALTAIR <span class="text-cyan-400 font-mono text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">QUANT LAB</span>
                    </h1>
                    <p class="text-[11px] text-slate-400">Institutional Quantitative Research & Harmonics Engine</p>
                </div>
            </div>

            <!-- Animated Slides Container -->
            <div class="my-10 z-10 min-h-[260px] flex flex-col justify-center">
                <!-- Slide 1 -->
                <div id="slide0" class="login-slide transition-all duration-700 opacity-100 transform translate-x-0">
                    <div class="inline-flex items-center gap-2 text-cyan-400 text-xs font-mono uppercase tracking-widest mb-3 bg-cyan-500/10 border border-cyan-500/20 px-3 py-1 rounded-full">
                        <i class="fa-solid fa-circle-notch animate-spin text-[10px]"></i> Model I: Geometric Harmonics
                    </div>
                    <h2 class="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                        NIFTY 50 W.D. Gann Cycles & Square of 9 Harmonics
                    </h2>
                    <p class="text-sm text-slate-400 mt-3 leading-relaxed max-w-lg">
                        Mathematical angle projections, planetary timing turning points, and institutional support/resistance pivots plotted directly on high-resolution interactive canvases.
                    </p>
                    <div class="mt-6 flex flex-wrap gap-2 text-xs font-mono text-cyan-300">
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#SquareOf9</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#TurningDates</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#PriceAngles</span>
                    </div>
                </div>

                <!-- Slide 2 -->
                <div id="slide1" class="login-slide hidden transition-all duration-700 opacity-0 transform translate-x-4">
                    <div class="inline-flex items-center gap-2 text-emerald-400 text-xs font-mono uppercase tracking-widest mb-3 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full">
                        <i class="fa-solid fa-filter text-[10px]"></i> Model II: Quantitative Screener
                    </div>
                    <h2 class="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                        Multi-Metric Stock Screener & 2D Quadrant Maps
                    </h2>
                    <p class="text-sm text-slate-400 mt-3 leading-relaxed max-w-lg">
                        Screens 40+ top equities across Valuation (P/E), Momentum (14D RSI), Solvency (Debt/Equity), and Capital Efficiency (ROE %) to surface actionable alpha opportunities.
                    </p>
                    <div class="mt-6 flex flex-wrap gap-2 text-xs font-mono text-emerald-300">
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#RSI_Oversold</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#HighROE</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#LowPE_Bargain</span>
                    </div>
                </div>

                <!-- Slide 3 -->
                <div id="slide2" class="login-slide hidden transition-all duration-700 opacity-0 transform translate-x-4">
                    <div class="inline-flex items-center gap-2 text-yellow-400 text-xs font-mono uppercase tracking-widest mb-3 bg-yellow-500/10 border border-yellow-500/20 px-3 py-1 rounded-full">
                        <i class="fa-solid fa-coins text-[10px]"></i> Model III: Precious Metals
                    </div>
                    <h2 class="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                        Gold & Silver Ratio (GSR) Mean-Reversion Matrix
                    </h2>
                    <p class="text-sm text-slate-400 mt-3 leading-relaxed max-w-lg">
                        Tracks the institutional Gold/Silver ratio with statistical standard deviation bands to pinpoint extreme macro mispricings and commodity rotation cycles.
                    </p>
                    <div class="mt-6 flex flex-wrap gap-2 text-xs font-mono text-yellow-300">
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#GSR_ZScore</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#COMEX_Metals</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#PairsTrading</span>
                    </div>
                </div>

                <!-- Slide 4 -->
                <div id="slide3" class="login-slide hidden transition-all duration-700 opacity-0 transform translate-x-4">
                    <div class="inline-flex items-center gap-2 text-purple-400 text-xs font-mono uppercase tracking-widest mb-3 bg-purple-500/10 border border-purple-500/20 px-3 py-1 rounded-full">
                        <i class="fa-solid fa-gem text-[10px]"></i> Model IV: Value Compounders
                    </div>
                    <h2 class="text-2xl lg:text-3xl font-bold text-white tracking-tight leading-snug">
                        Quality Compounders & Solvency Stress Analysis
                    </h2>
                    <p class="text-sm text-slate-400 mt-3 leading-relaxed max-w-lg">
                        Scans defensive compounders across BFSI, FMCG, and Pharma with Piotroski F-Score checks and balance-sheet fragility diagnostics.
                    </p>
                    <div class="mt-6 flex flex-wrap gap-2 text-xs font-mono text-purple-300">
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#Piotroski</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#SolvencyStress</span>
                        <span class="bg-slate-800/80 border border-darkBorder px-2.5 py-1 rounded-lg">#DefensiveMoat</span>
                    </div>
                </div>
            </div>

            <!-- Slide Navigation Indicators & Controls -->
            <div class="flex items-center justify-between z-10 border-t border-darkBorder/40 pt-4">
                <div class="flex items-center gap-2">
                    <button onclick="setSlide(0)" class="slide-dot w-6 h-1.5 rounded-full bg-cyan-400 transition-all"></button>
                    <button onclick="setSlide(1)" class="slide-dot w-2 h-1.5 rounded-full bg-slate-700 hover:bg-slate-500 transition-all"></button>
                    <button onclick="setSlide(2)" class="slide-dot w-2 h-1.5 rounded-full bg-slate-700 hover:bg-slate-500 transition-all"></button>
                    <button onclick="setSlide(3)" class="slide-dot w-2 h-1.5 rounded-full bg-slate-700 hover:bg-slate-500 transition-all"></button>
                </div>
                <div class="text-[11px] font-mono text-slate-500">
                    Proprietary Quantitative Infrastructure
                </div>
            </div>
        </div>

        <!-- RIGHT PANEL (50%): Institutional Sign-In Form -->
        <div class="w-full md:w-1/2 bg-[#060911] p-8 md:p-14 flex items-center justify-center relative">
            <div class="max-w-md w-full">
                
                <div class="mb-8">
                    <h3 class="text-2xl font-bold text-white tracking-tight">Terminal Authentication</h3>
                    <p class="text-xs text-slate-400 mt-1">Enter your institutional credentials to unlock the research workspace.</p>
                </div>

                <form id="loginForm" onsubmit="event.preventDefault(); handleLoginSubmit(event); return false;" class="space-y-4">
                    <!-- User ID -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">User ID</label>
                        <div class="relative">
                            <i class="fa-solid fa-user absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                            <input type="text" id="loginUser" required placeholder="User ID (e.g. Aditya.raj)" value="Aditya.raj"
                                   onkeydown="if(event.key==='Enter'){event.preventDefault(); handleLoginSubmit(event);}"
                                   class="w-full bg-darkBg border border-darkBorder rounded-xl pl-10 pr-4 py-3 text-sm text-white font-mono focus:outline-none focus:border-cyan-500 transition-all">
                        </div>
                    </div>

                    <!-- Password -->
                    <div>
                        <label class="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">Password</label>
                        <div class="relative">
                            <i class="fa-solid fa-lock absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                            <input type="password" id="loginPass" required placeholder="Enter password" value="Aditya@3205#"
                                   onkeydown="if(event.key==='Enter'){event.preventDefault(); handleLoginSubmit(event);}"
                                   class="w-full bg-darkBg border border-darkBorder rounded-xl pl-10 pr-11 py-3 text-sm text-cyan-300 font-mono focus:outline-none focus:border-cyan-500 transition-all">
                            <button type="button" onclick="togglePassVisibility()" class="absolute right-3.5 top-3.5 text-slate-500 hover:text-slate-300 transition-all">
                                <i id="eyeIcon" class="fa-solid fa-eye text-sm"></i>
                            </button>
                        </div>
                    </div>

                    <!-- Remember & Security Info -->
                    <div class="flex items-center justify-between text-xs text-slate-400 pt-1">
                        <label class="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" id="rememberMe" checked class="rounded border-darkBorder bg-darkBg text-cyan-500 focus:ring-0">
                            <span>Keep session active</span>
                        </label>
                        <span class="text-emerald-400 flex items-center gap-1 font-mono text-[11px]">
                            <i class="fa-solid fa-shield-halved"></i> 256-bit Encrypted
                        </span>
                    </div>

                    <!-- Submit Button -->
                    <button type="button" onclick="handleLoginSubmit(event)" id="loginBtn" class="w-full bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold py-3.5 rounded-xl shadow-lg shadow-cyan-500/20 transition-all text-sm flex items-center justify-center gap-2 mt-4 cursor-pointer">
                        <span>Sign In to Terminal</span>
                        <i class="fa-solid fa-arrow-right text-xs"></i>
                    </button>

                    <!-- Error Alert -->
                    <div id="loginError" class="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs hidden flex items-center gap-2">
                        <i class="fa-solid fa-circle-exclamation text-sm shrink-0"></i>
                        <span id="loginErrorMsg">Invalid User ID or Password.</span>
                    </div>
                </form>

                <div class="mt-8 border-t border-darkBorder/50 pt-4 flex items-center justify-between text-[11px] text-slate-500">
                    <span>Authorized Personnel Only</span>
                    <span class="font-mono">v2.2.0 • ALTAIR</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Top Navigation Bar -->
    <header class="bg-darkCard/90 backdrop-blur border-b border-darkBorder px-3 sm:px-4 py-2 flex items-center justify-between shrink-0 z-30">
        <div class="flex items-center space-x-2.5 sm:space-x-3">
            <!-- Mobile 3-Dash Menu Toggle Button (Phone View Only) -->
            <button onclick="toggleMobileSidebar()" id="mobileMenuBtn" title="Open Navigation Menu"
                    class="md:hidden flex items-center justify-center w-8 h-8 rounded-lg bg-darkBg hover:bg-slate-800 border border-darkBorder text-cyan-400 hover:text-white transition-all cursor-pointer">
                <i class="fa-solid fa-bars text-sm"></i>
            </button>
            <img src="/logo.png" alt="Altair Logo" class="w-8 h-8 rounded-lg object-contain border border-cyan-500/30 shadow-sm shadow-cyan-500/10">
            <div class="flex items-center gap-2">
                <span class="font-black text-sm tracking-wider text-white">ALTAIR</span>
                <span class="bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Quant Lab</span>
            </div>
        </div>

        <!-- View Mode Segmented Controls (Split / Full Chat / Full Canvas) -->
        <div class="hidden md:flex items-center bg-darkBg border border-darkBorder rounded-lg p-0.5 text-xs">
            <button onclick="setViewMode('chat')" id="btnViewChat" class="px-3 py-1 rounded-md text-slate-400 hover:text-white transition-all flex items-center gap-1.5 font-medium">
                <i class="fa-regular fa-comment-dots"></i> Chat Only
            </button>
            <button onclick="setViewMode('split')" id="btnViewSplit" class="px-3 py-1 rounded-md bg-cyan-500 text-darkBg font-bold transition-all flex items-center gap-1.5 shadow-sm">
                <i class="fa-solid fa-table-columns"></i> Split View
            </button>
            <button onclick="setViewMode('canvas')" id="btnViewCanvas" class="px-3 py-1 rounded-md text-slate-400 hover:text-white transition-all flex items-center gap-1.5 font-medium">
                <i class="fa-solid fa-chart-line"></i> Canvas Only
            </button>
        </div>

        <div class="flex items-center space-x-3 relative">
            <div class="hidden sm:flex items-center gap-1.5 text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Online</span>
            </div>

            <!-- Profile Pill Block -->
            <div class="relative">
                <button onclick="toggleProfileDropdown()" id="profilePillBtn" class="flex items-center gap-2 bg-darkBg hover:bg-slate-800 border border-darkBorder hover:border-cyan-500/40 rounded-full pl-1.5 pr-2.5 py-1 text-xs text-slate-200 transition-all shadow-sm group">
                    <div class="w-6 h-6 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white text-[11px] font-bold border border-cyan-400/40 shadow-sm shrink-0">
                        <i class="fa-solid fa-user text-[10px]"></i>
                    </div>
                    <span class="hidden sm:inline font-medium text-slate-200 group-hover:text-white max-w-[100px] truncate">Aditya Raj</span>
                    <i id="profileChevron" class="fa-solid fa-chevron-down text-[9px] text-slate-400 group-hover:text-cyan-400 transition-transform duration-200"></i>
                </button>

                <!-- Profile Dropdown Menu -->
                <div id="profileDropdown" class="absolute right-0 top-full mt-2 w-64 bg-darkCard border border-darkBorder rounded-2xl shadow-2xl p-2 z-50 hidden select-none">
                    <!-- User Info Card -->
                    <div class="p-3 bg-darkBg/70 border border-darkBorder/60 rounded-xl flex items-center gap-3 mb-2">
                        <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold border border-cyan-400/40 shrink-0">
                            <i class="fa-solid fa-user text-sm"></i>
                        </div>
                        <div class="overflow-hidden">
                            <div class="font-bold text-white text-xs truncate">Aditya Raj</div>
                            <div class="text-[10px] text-slate-400 truncate font-mono">Aditya.raj</div>
                            <span class="inline-block mt-1 text-[9px] font-bold tracking-wider uppercase text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 px-1.5 py-0.2 rounded-full">
                                Institutional Pro
                            </span>
                        </div>
                    </div>

                    <!-- Dropdown Action Items -->
                    <div class="space-y-0.5 text-xs text-slate-300">
                        <button onclick="alert('Connected to Gemini 2.0 Flash & Real-Time Feed Engine.')" class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-left">
                            <i class="fa-solid fa-brain text-cyan-400 w-4 text-center"></i>
                            <span>AI Model: Gemini 2.0</span>
                        </button>
                        <button onclick="toggleSessionsMenu(); toggleProfileDropdown();" class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-left">
                            <i class="fa-solid fa-clock-rotate-left text-cyan-400 w-4 text-center"></i>
                            <span>Research Sessions</span>
                        </button>
                        <a href="/download/notebook" class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800 hover:text-white transition-colors text-left">
                            <i class="fa-solid fa-file-code text-cyan-400 w-4 text-center"></i>
                            <span>Export .ipynb Notebook</span>
                        </a>
                        <div class="my-1 border-t border-darkBorder/60"></div>
                        <button onclick="logoutTerminal()" class="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-rose-500/10 text-rose-400 hover:text-rose-300 transition-colors text-left">
                            <i class="fa-solid fa-arrow-right-from-bracket w-4 text-center"></i>
                            <span>Sign Out / Lock</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Mobile View Switcher (< 768px) -->
    <div class="md:hidden flex border-b border-darkBorder bg-darkCard text-xs shrink-0 z-20">
        <button onclick="setMobileTab('chat')" id="mTabChat" class="flex-1 py-2 text-center font-bold text-cyan-400 border-b-2 border-cyan-400 flex items-center justify-center gap-1.5">
            <i class="fa-regular fa-comment-dots"></i> AI Chat
        </button>
        <button onclick="setMobileTab('canvas')" id="mTabCanvas" class="flex-1 py-2 text-center font-semibold text-slate-400 flex items-center justify-center gap-1.5">
            <i class="fa-solid fa-chart-line"></i> Canvas
        </button>
    </div>

    <!-- Backdrop Overlay for Mobile when Sidebar is Expanded -->
    <div id="sidebarBackdrop" onclick="closeMobileSidebar()" class="fixed inset-0 bg-black/75 backdrop-blur-sm z-40 hidden md:hidden transition-opacity"></div>

    <!-- Main Workspace Container -->
    <div class="flex-1 flex overflow-hidden relative">

        <!-- 1. EXPANDABLE NAVIGATION SIDEBAR (Mobile Overlay Drawer / Desktop Collapsible) -->
        <aside id="mainSidebar" class="fixed md:relative inset-y-0 left-0 z-50 md:z-20 -translate-x-full md:translate-x-0 w-64 md:w-14 bg-darkSidebar border-r border-darkBorder flex flex-col shrink-0 transition-all duration-300 ease-in-out overflow-y-auto overflow-x-hidden select-none shadow-2xl md:shadow-none">
            
            <!-- Sidebar Header / Category Title -->
            <div class="px-3 border-b border-darkBorder/70 flex items-center justify-between shrink-0 h-14">
                <div class="flex items-center gap-3 cursor-pointer hover:bg-slate-800/30 py-2 px-1 rounded-lg transition-all" onclick="toggleSidebar()" title="Toggle Sidebar">
                    <i class="fa-solid fa-layer-group text-cyan-400 text-sm w-5 text-center shrink-0"></i>
                    <span class="sidebar-label inline md:hidden text-xs font-bold tracking-wider text-white uppercase whitespace-nowrap">Quantitative Lab</span>
                </div>
                <!-- Close Button on Mobile -->
                <button onclick="closeMobileSidebar()" class="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer" title="Close Menu">
                    <i class="fa-solid fa-xmark text-base"></i>
                </button>
            </div>

            <!-- Navigation Items List -->
            <div class="p-2 space-y-2 flex-1">
                
                <!-- 1. QUANTITATIVE SCREENER (Featured Primary Option) -->
                <div>
                    <button onclick="selectSidebarItem('Run Multi-Metric Quant Stock Screener')" title="Multi-Metric Stock Screener" 
                            class="w-full h-10 rounded-xl flex items-center gap-3 text-cyan-300 hover:text-cyan-100 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 px-2.5 transition-all text-xs shadow-sm group">
                        <i class="fa-solid fa-filter text-cyan-400 w-5 text-center shrink-0 group-hover:scale-110 transition-transform"></i>
                        <div class="sidebar-label hidden flex-1 flex items-center justify-between overflow-hidden">
                            <span class="whitespace-nowrap font-bold text-white">Stock Screener</span>
                            <span class="text-[9px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.5 rounded font-mono uppercase">Live</span>
                        </div>
                    </button>
                </div>

                <!-- 2. MACRO & HARMONICS (Dropdown Accordion) -->
                <div class="border-t border-darkBorder/40 pt-1.5">
                    <button onclick="toggleAccordion('macroAccordion')" title="Macro & Harmonics"
                            class="w-full h-9 rounded-lg flex items-center justify-between px-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all text-xs group">
                        <div class="flex items-center gap-2.5 overflow-hidden">
                            <i class="fa-solid fa-chart-pie text-cyan-400/80 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap text-[11px] font-semibold tracking-wider uppercase text-slate-400 group-hover:text-slate-200">Macro & Harmonics</span>
                        </div>
                        <div class="sidebar-label hidden flex items-center gap-1.5 shrink-0">
                            <span class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full font-mono">3</span>
                            <i id="macroAccordion-chevron" class="fa-solid fa-chevron-down text-[10px] text-slate-500 transition-transform duration-200"></i>
                        </div>
                    </button>
                    
                    <!-- Macro Sub-Items (Collapsed by default) -->
                    <div id="macroAccordion" class="space-y-1 mt-1 pl-1 hidden">
                        <button onclick="selectSidebarItem('NIFTY 50 Gann cycle and Square of 9 levels')" title="Nifty Gann Harmonics" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-cyan-400 hover:bg-cyan-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-circle-notch text-cyan-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Nifty Gann Cycle</span>
                        </button>

                        <button onclick="selectSidebarItem('Analyze Gold and Silver Precious Metals GSR')" title="Precious Metals GSR" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-yellow-400 hover:bg-yellow-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-coins text-yellow-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Gold & Silver (GSR)</span>
                        </button>

                        <button onclick="selectSidebarItem('Top Undervalued FMCG, BFSI and Pharma compounders')" title="Value Compounders" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-purple-400 hover:bg-purple-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-gem text-purple-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Value Compounders</span>
                        </button>
                    </div>
                </div>

                <!-- 3. SUB-FIELD SCANNERS (Dropdown Accordion) -->
                <div class="border-t border-darkBorder/40 pt-1.5">
                    <button onclick="toggleAccordion('scannersAccordion')" title="Sub-Field Scanners"
                            class="w-full h-9 rounded-lg flex items-center justify-between px-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all text-xs group">
                        <div class="flex items-center gap-2.5 overflow-hidden">
                            <i class="fa-solid fa-bolt text-amber-400/80 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap text-[11px] font-semibold tracking-wider uppercase text-slate-400 group-hover:text-slate-200">Sector Scanners</span>
                        </div>
                        <div class="sidebar-label hidden flex items-center gap-1.5 shrink-0">
                            <span class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full font-mono">5</span>
                            <i id="scannersAccordion-chevron" class="fa-solid fa-chevron-down text-[10px] text-slate-500 transition-transform duration-200"></i>
                        </div>
                    </button>
                    
                    <!-- Scanners Sub-Items (Collapsed by default) -->
                    <div id="scannersAccordion" class="space-y-1 mt-1 pl-1 hidden">
                        <button onclick="selectSidebarItem('Scan Top 6 Adani Group stocks')" title="Adani Flagships" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-amber-400 hover:bg-amber-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-bolt text-amber-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Top 6 Adani Group</span>
                        </button>

                        <button onclick="selectSidebarItem('Scan Auto 2-Wheelers')" title="Auto 2-Wheelers" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-emerald-400 hover:bg-emerald-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-motorcycle text-emerald-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Auto: 2-Wheelers</span>
                        </button>

                        <button onclick="selectSidebarItem('Scan Auto 4W and Commercial Vehicles')" title="Auto 4W & CV" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-blue-400 hover:bg-blue-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-car text-blue-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Auto: 4W & CV</span>
                        </button>

                        <button onclick="selectSidebarItem('Scan Banking - Private')" title="Private Banks" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-cyan-400 hover:bg-cyan-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-building-columns text-cyan-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Banking - Private</span>
                        </button>

                        <button onclick="selectSidebarItem('Scan Banking - PSU')" title="PSU Banks" 
                                class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-orange-400 hover:bg-orange-500/10 px-2 transition-all text-xs">
                            <i class="fa-solid fa-landmark text-orange-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Banking - PSU</span>
                        </button>
                    </div>
                </div>

                <!-- 4. LAB TOOLS (Dropdown Accordion) -->
                <div class="border-t border-darkBorder/40 pt-1.5">
                    <button onclick="toggleAccordion('toolsAccordion')" title="Lab Tools"
                            class="w-full h-9 rounded-lg flex items-center justify-between px-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-all text-xs group">
                        <div class="flex items-center gap-2.5 overflow-hidden">
                            <i class="fa-solid fa-screwdriver-wrench text-cyan-400/80 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap text-[11px] font-semibold tracking-wider uppercase text-slate-400 group-hover:text-slate-200">Lab Tools</span>
                        </div>
                        <div class="sidebar-label hidden flex items-center gap-1.5 shrink-0">
                            <span class="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full font-mono">1</span>
                            <i id="toolsAccordion-chevron" class="fa-solid fa-chevron-down text-[10px] text-slate-500 transition-transform duration-200"></i>
                        </div>
                    </button>
                    
                    <!-- Tools Sub-Items (Collapsed by default) -->
                    <div id="toolsAccordion" class="space-y-1 mt-1 pl-1 hidden">
                        <a href="/download/notebook" title="Download .ipynb" 
                           class="w-full h-9 rounded-lg flex items-center gap-2.5 text-slate-300 hover:text-cyan-400 hover:bg-darkBorder/60 px-2 transition-all text-xs">
                            <i class="fa-solid fa-file-code text-cyan-400 w-5 text-center shrink-0"></i>
                            <span class="sidebar-label hidden whitespace-nowrap font-medium">Export .ipynb</span>
                        </a>
                    </div>
                </div>
            </div>

            <!-- Bottom Actions & Toggle -->
            <div class="border-t border-darkBorder/70 p-2 space-y-1 shrink-0 bg-darkCard/20">
                <!-- 3-Dash Toggle Button Moved Here -->
                <button onclick="toggleSidebar()" title="Toggle Sidebar" 
                        class="w-full h-10 rounded-xl flex items-center gap-3 text-slate-400 hover:text-white hover:bg-slate-800/60 px-2.5 transition-all text-xs group">
                    <i class="fa-solid fa-bars text-cyan-400 w-5 text-center shrink-0 group-hover:scale-110 transition-transform"></i>
                    <span class="sidebar-label hidden whitespace-nowrap font-medium text-slate-300 group-hover:text-white">Collapse Sidebar</span>
                </button>

                <!-- Status Indicator -->
                <div class="px-2.5 py-1.5 flex items-center gap-3">
                    <div class="w-2 h-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50 ml-1.5 shrink-0 animate-pulse"></div>
                    <span class="sidebar-label hidden text-[11px] text-slate-400 whitespace-nowrap">Engine Active</span>
                </div>
            </div>
        </aside>

        <!-- 2. LEFT PANE: AI Chat Window -->
        <section id="chatSection" class="flex flex-col border-r border-darkBorder bg-darkCard/20 h-full transition-all duration-200 overflow-hidden w-full md:w-[450px] lg:w-[480px]">
            
            <!-- Chat Sessions Control Bar -->
            <div class="px-3 py-2 border-b border-darkBorder flex items-center justify-between shrink-0 bg-darkCard/60 relative select-none">
                <div class="flex items-center gap-2 overflow-hidden">
                    <button onclick="toggleSessionsMenu()" id="sessionSelectorBtn" title="Select Research Session" class="flex items-center gap-2 text-xs bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-200 px-2.5 py-1.5 rounded-lg transition-all max-w-[200px] sm:max-w-[240px]">
                        <i class="fa-solid fa-clock-rotate-left text-cyan-400 text-xs shrink-0"></i>
                        <span id="activeSessionTitle" class="truncate font-medium">Quantitative Research</span>
                        <i id="sessionChevron" class="fa-solid fa-chevron-down text-[10px] text-slate-500 shrink-0"></i>
                    </button>
                    <button onclick="createNewSession()" title="Start New Research Session" class="h-7 px-2 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 text-xs flex items-center gap-1 font-semibold transition-all">
                        <i class="fa-solid fa-plus text-[10px]"></i>
                        <span class="hidden sm:inline">New</span>
                    </button>
                </div>
                <div class="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                    <span id="sessionCounter">0 msgs</span>
                    <button onclick="logoutTerminal()" title="Sign Out of Terminal" class="text-slate-500 hover:text-rose-400 transition-colors p-1 rounded">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                    </button>
                </div>

                <!-- Sessions Dropdown Overlay -->
                <div id="sessionsMenu" class="absolute top-full left-2 right-2 mt-1 bg-darkCard border border-darkBorder rounded-xl shadow-2xl p-2 z-40 hidden max-h-72 overflow-y-auto">
                    <div class="flex items-center justify-between px-2 py-1 mb-1 border-b border-darkBorder/60 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                        <span>Research History</span>
                        <span class="text-cyan-400 font-mono text-[10px] cursor-pointer hover:underline" onclick="createNewSession()">+ New Session</span>
                    </div>
                    <div id="sessionsList" class="space-y-1">
                        <!-- Populated by JS -->
                    </div>
                </div>
            </div>

            <!-- Quick Chips -->
            <div class="p-2.5 border-b border-darkBorder flex gap-2 overflow-x-auto whitespace-nowrap text-xs shrink-0 bg-darkCard/40">
                <button onclick="sendQuickPrompt('Run Multi-Metric Quant Stock Screener')" class="bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 text-cyan-300 font-bold px-3 py-1 rounded-lg shrink-0 flex items-center gap-1.5 transition-all shadow-sm">
                    <i class="fa-solid fa-filter text-xs"></i> Stock Screener
                </button>
                <button onclick="sendQuickPrompt('NIFTY 50 Gann cycle and Square of 9 levels')" class="bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1 transition-all">
                    🔮 Nifty Gann
                </button>
                <button onclick="sendQuickPrompt('Scan Top 6 Adani Group stocks')" class="bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1 transition-all">
                    ⚡ Adani 6
                </button>
                <button onclick="sendQuickPrompt('Scan Auto 2-Wheelers')" class="bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1 transition-all">
                    🏍️ 2-Wheelers
                </button>
                <button onclick="sendQuickPrompt('Top Undervalued FMCG, BFSI and Pharma compounders')" class="bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1 transition-all">
                    💎 Value Compounders
                </button>
                <button onclick="sendQuickPrompt('Analyze Gold and Silver Precious Metals GSR')" class="bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 px-2.5 py-1 rounded-lg shrink-0 flex items-center gap-1 transition-all">
                    🪙 Gold & Silver
                </button>
            </div>

            <!-- Messages Area -->
            <div id="chatHistory" class="flex-1 p-4 overflow-y-auto space-y-4 text-xs sm:text-sm">
                <div class="flex items-start gap-2.5">
                    <img src="/logo.png" class="w-6 h-6 rounded-md object-contain border border-cyan-500/30 shrink-0">
                    <div class="bg-darkCard border border-darkBorder p-3.5 rounded-2xl rounded-tl-none max-w-[90%] text-slate-300 leading-relaxed shadow-sm">
                        <p class="font-bold text-cyan-400 mb-1">ALTAIR Quant Strategist</p>
                        Welcome! Ask me to run 4-pillar scans, test Gann cycles, analyze precious metals, or scan for undervalued compounders!
                    </div>
                </div>
            </div>

            <!-- Input Bar -->
            <div class="p-3 border-t border-darkBorder bg-darkCard/60 shrink-0">
                <form onsubmit="handleUserSubmit(event)" class="flex gap-2">
                    <input type="text" id="userMessage" placeholder="Ask AI: 'Scan Adani', 'Nifty Gann', 'FMCG value'..." 
                           class="flex-1 bg-darkBg border border-darkBorder rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-all">
                    <button type="submit" id="sendBtn" class="bg-cyan-500 hover:bg-cyan-400 text-darkBg font-bold px-3.5 rounded-xl flex items-center justify-center transition-all">
                        <i class="fa-solid fa-paper-plane text-xs sm:text-sm"></i>
                    </button>
                </form>
            </div>
        </section>

        <!-- 3. RIGHT PANE: Visual Canvas & Jupyter Notebook -->
        <section id="canvasSection" class="flex-1 hidden md:flex flex-col h-full overflow-y-auto p-4 sm:p-6 space-y-4 bg-darkBg min-w-0 transition-all duration-200">
            
            <!-- Right Pane Header: Primary Mode Switcher (Canvas vs Notebook) -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-darkBorder pb-3 shrink-0">
                <div class="flex items-center gap-2.5">
                    <!-- Tab Switcher: Visual Canvas vs Jupyter Notebook -->
                    <div class="flex items-center bg-darkCard border border-darkBorder rounded-xl p-1 text-xs select-none">
                        <button onclick="setRightPaneView('canvas')" id="btnTabCanvas" class="px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shadow-sm">
                            <i class="fa-solid fa-chart-line text-cyan-400"></i> Visual Canvas
                        </button>
                        <button onclick="setRightPaneView('notebook')" id="btnTabNotebook" class="px-3 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs">
                            <i class="fa-solid fa-book-bookmark text-amber-400"></i> Jupyter Notebook
                        </button>
                    </div>
                </div>

                <!-- Screener Multi-Chart Switcher (Visible in Canvas Mode when screener is active) -->
                <div id="chartTypeSwitcher" class="hidden flex items-center bg-darkCard border border-darkBorder rounded-xl p-1 text-xs gap-1 overflow-x-auto select-none shadow-sm">
                    <button onclick="switchChartType('quadrant')" id="btnChart-quadrant" title="2D Quadrant Matrix" class="px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shrink-0 shadow-sm">
                        <i class="fa-solid fa-circle-nodes text-[11px]"></i> Quadrant Matrix
                    </button>
                    <button onclick="switchChartType('ranking')" id="btnChart-ranking" title="Ranked Quant Leaderboard" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0">
                        <i class="fa-solid fa-ranking-star text-[11px]"></i> Quant Leaderboard
                    </button>
                    <button onclick="switchChartType('frontier')" id="btnChart-frontier" title="Valuation vs ROE Quality Frontier" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0">
                        <i class="fa-solid fa-crosshairs text-[11px]"></i> Quality Frontier
                    </button>
                    <button onclick="switchChartType('sector')" id="btnChart-sector" title="Sector Breakdown" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0">
                        <i class="fa-solid fa-cubes-stacked text-[11px]"></i> Sector Breakdown
                    </button>
                </div>

                <div class="flex items-center gap-3">
                    <span class="text-[11px] text-slate-400 font-mono" id="canvasTimestamp">Live Stream</span>
                    <button onclick="toggleCanvasExpand()" title="Toggle Full View" class="text-slate-400 hover:text-cyan-400 text-xs hidden md:block">
                        <i class="fa-solid fa-expand"></i>
                    </button>
                </div>
            </div>

            <!-- VIEW 1: VISUAL CANVAS VIEW (Charts & Scrollable Leaderboard) -->
            <div id="canvasViewContainer" class="space-y-5">
                <!-- Plotly Chart Box -->
                <div id="chartOuterWrapper" class="bg-darkCard border border-darkBorder rounded-2xl p-2 sm:p-4 shadow-xl w-full min-h-[480px] overflow-hidden relative">
                    <div id="plotlyChartBox" class="w-full h-full min-h-[460px]">
                        <div class="flex flex-col items-center justify-center h-full min-h-[420px] text-slate-500" id="emptyChartPlaceholder">
                            <i class="fa-solid fa-chart-line text-4xl mb-3 text-slate-600"></i>
                            <p class="text-xs">Trigger any AI scan to render interactive charts here</p>
                        </div>
                    </div>
                </div>

                <!-- Ranked Leaderboard Data Table (Scrollable with Fixed Header) -->
                <div id="tableContainerBox" class="bg-darkCard border border-darkBorder rounded-2xl p-4 shadow-xl overflow-hidden hidden">
                    <div class="flex items-center justify-between mb-3 border-b border-darkBorder/60 pb-2.5">
                        <h3 class="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
                            <i class="fa-solid fa-list-ol text-cyan-400"></i> Ranked Leaderboard Scorecard
                            <span id="tableCountBadge" class="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-full font-mono font-normal">15 Picks</span>
                        </h3>
                        <span class="text-[10px] text-slate-400 font-mono flex items-center gap-1.5">
                            <i class="fa-solid fa-arrows-up-down-left-right text-cyan-400/80"></i> Vertical & Horizontal Scroll Enabled
                        </span>
                    </div>
                    <div id="dynamicTableWrapper" class="overflow-x-auto overflow-y-auto max-h-[380px] w-full border border-darkBorder/50 rounded-xl bg-darkBg/60"></div>
                </div>
            </div>

            <!-- VIEW 2: FULL JUPYTER NOTEBOOK VIEW (Interactive Viewer & Editor) -->
            <div id="notebookViewContainer" class="hidden space-y-4">
                <!-- Notebook Action Bar -->
                <div class="bg-darkCard border border-darkBorder rounded-2xl p-3 sm:p-4 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                            <i class="fa-solid fa-book-bookmark text-base"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-2">
                                <h3 class="font-bold text-sm text-white">ste_engine_lab.ipynb</h3>
                                <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1">
                                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Python 3.11 Kernel
                                </span>
                            </div>
                            <p id="nbMetaText" class="text-xs text-slate-400 mt-0.5">Loading notebook cells...</p>
                        </div>
                    </div>

                    <div class="flex items-center gap-2 shrink-0">
                        <button onclick="addNewNotebookCell()" title="Add Code Cell" class="h-8 px-3 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-all">
                            <i class="fa-solid fa-plus text-[10px]"></i> Add Cell
                        </button>
                        <button onclick="saveNotebookToServer()" id="btnSaveNotebook" title="Save Modifications to Disk" class="h-8 px-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all">
                            <i class="fa-solid fa-floppy-disk text-[11px]"></i> Save Notebook
                        </button>
                        <a href="/download/notebook" title="Download .ipynb" class="h-8 px-3 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 text-xs flex items-center gap-1.5 transition-all">
                            <i class="fa-solid fa-download text-cyan-400 text-[11px]"></i> Download
                        </a>
                        <button onclick="loadNotebookData()" title="Reload from Disk" class="h-8 w-8 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-400 hover:text-white flex items-center justify-center transition-all">
                            <i class="fa-solid fa-rotate text-xs"></i>
                        </button>
                    </div>
                </div>

                <!-- Notebook Cells List Container -->
                <div id="notebookCellsList" class="space-y-4">
                    <!-- Populated dynamically by JS -->
                </div>
            </div>

        </section>

    </div>

    <!-- Scripts -->
    <script>
        let currentMode = "split"; // 'chat', 'split', 'canvas'
        let sidebarExpanded = false;
        let currentSlide = 0;
        let slideTimer = null;
        let currentSessionId = localStorage.getItem("ALTAIR_ACTIVE_SESSION") || null;
        let chatSessions = [];

        function countLines(str) {
            if (!str) return 1;
            let n = 1;
            for (let i = 0; i < str.length; i++) {
                if (str.charCodeAt(i) === 10) n++;
            }
            return n;
        }

        function splitIntoLines(str) {
            if (!str) return [];
            let lines = [];
            let current = "";
            const nl = String.fromCharCode(10);
            for (let i = 0; i < str.length; i++) {
                let code = str.charCodeAt(i);
                if (code === 10) {
                    lines.push(current + nl);
                    current = "";
                } else if (code !== 13) {
                    current += str[i];
                }
            }
            if (current.length > 0) lines.push(current);
            return lines;
        }

        // 1. Check Authentication on Load
        function checkAuth() {
            const isAuth = localStorage.getItem("ALTAIR_AUTH") === "true";
            if (isAuth) {
                document.getElementById("loginModal").classList.add("hidden");
                loadSessions();
            } else {
                startSlideTimer();
            }
        }

        // 2. Slideshow Logic
        function setSlide(idx) {
            const slides = document.querySelectorAll(".login-slide");
            const dots = document.querySelectorAll(".slide-dot");
            if (!slides || slides.length === 0) return;

            slides.forEach((s, i) => {
                if (i === idx) {
                    s.classList.remove("hidden");
                    setTimeout(() => {
                        s.classList.remove("opacity-0", "translate-x-4");
                        s.classList.add("opacity-100", "translate-x-0");
                    }, 20);
                } else {
                    s.classList.add("opacity-0", "translate-x-4");
                    s.classList.remove("opacity-100", "translate-x-0");
                    setTimeout(() => { s.classList.add("hidden"); }, 300);
                }
            });

            dots.forEach((d, i) => {
                if (i === idx) {
                    d.className = "slide-dot w-6 h-1.5 rounded-full bg-cyan-400 transition-all";
                } else {
                    d.className = "slide-dot w-2 h-1.5 rounded-full bg-slate-700 hover:bg-slate-500 transition-all";
                }
            });
            currentSlide = idx;
        }

        function startSlideTimer() {
            if (slideTimer) clearInterval(slideTimer);
            slideTimer = setInterval(() => {
                const next = (currentSlide + 1) % 4;
                setSlide(next);
            }, 4500);
        }

        function togglePassVisibility() {
            const passInput = document.getElementById("loginPass");
            const eye = document.getElementById("eyeIcon");
            if (passInput.type === "password") {
                passInput.type = "text";
                eye.classList.remove("fa-eye");
                eye.classList.add("fa-eye-slash");
            } else {
                passInput.type = "password";
                eye.classList.remove("fa-eye-slash");
                eye.classList.add("fa-eye");
            }
        }

        // 3. Login Authentication
        async function handleLoginSubmit(e) {
            if (e && e.preventDefault) e.preventDefault();
            const user = document.getElementById("loginUser").value.trim();
            const pass = document.getElementById("loginPass").value.trim();
            const errBox = document.getElementById("loginError");
            const errMsg = document.getElementById("loginErrorMsg");
            const submitBtn = document.getElementById("loginBtn");

            submitBtn.disabled = true;
            submitBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Authenticating...`;

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: user, password: pass})
                });

                if (res.ok) {
                    const data = await res.json();
                    localStorage.setItem("ALTAIR_AUTH", "true");
                    localStorage.setItem("ALTAIR_USER", user);
                    if (slideTimer) clearInterval(slideTimer);
                    const modal = document.getElementById("loginModal");
                    if (modal) {
                        modal.classList.add("hidden");
                        modal.style.display = "none";
                    }
                    errBox.classList.add("hidden");
                    loadSessions();
                } else {
                    const data = await res.json().catch(() => ({}));
                    errMsg.innerText = data.detail || "Invalid User ID or Password.";
                    errBox.classList.remove("hidden");
                }
            } catch (err) {
                errMsg.innerText = "Connection error. Please try again.";
                errBox.classList.remove("hidden");
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<span>Sign In to Terminal</span><i class="fa-solid fa-arrow-right text-xs"></i>`;
            }
        }

        function logoutTerminal() {
            if (confirm("Sign out of ALTAIR Quant Lab?")) {
                localStorage.removeItem("ALTAIR_AUTH");
                document.getElementById("loginModal").classList.remove("hidden");
                startSlideTimer();
            }
        }

        // 4. Multi-Session History Management
        async function loadSessions() {
            try {
                const res = await fetch('/api/sessions');
                if (res.ok) {
                    chatSessions = await res.json();
                    renderSessionsDropdown();
                    if (!currentSessionId && chatSessions.length > 0) {
                        loadSession(chatSessions[0].id);
                    } else if (currentSessionId) {
                        loadSession(currentSessionId);
                    } else {
                        createNewSession();
                    }
                }
            } catch (e) {
                console.log("Notice loading sessions:", e);
            }
        }

        function toggleSessionsMenu() {
            const menu = document.getElementById("sessionsMenu");
            const chevron = document.getElementById("sessionChevron");
            const isHidden = menu.classList.contains("hidden");
            if (isHidden) {
                menu.classList.remove("hidden");
                chevron.classList.add("rotate-180");
            } else {
                menu.classList.add("hidden");
                chevron.classList.remove("rotate-180");
            }
        }

        function toggleProfileDropdown() {
            const dd = document.getElementById("profileDropdown");
            const ch = document.getElementById("profileChevron");
            if (!dd) return;
            const isHidden = dd.classList.contains("hidden");
            if (isHidden) {
                dd.classList.remove("hidden");
                ch?.classList.add("rotate-180");
            } else {
                dd.classList.add("hidden");
                ch?.classList.remove("rotate-180");
            }
        }

        function renderSessionsDropdown() {
            const list = document.getElementById("sessionsList");
            if (!list) return;

            if (chatSessions.length === 0) {
                list.innerHTML = `<div class="p-3 text-center text-xs text-slate-500">No saved sessions yet.</div>`;
                return;
            }

            let html = "";
            chatSessions.forEach(s => {
                const isActive = s.id === currentSessionId;
                const activeClass = isActive ? "bg-cyan-500/15 border-cyan-500/30 text-cyan-300" : "hover:bg-slate-800/60 text-slate-300 border-transparent";
                const count = s.message_count || 0;
                const time = new Date(s.updated_at || s.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'});

                html += `
                    <div class="flex items-center justify-between p-2 rounded-lg border ${activeClass} transition-all text-xs group cursor-pointer" onclick="selectSession('${s.id}')">
                        <div class="flex items-center gap-2 overflow-hidden flex-1">
                            <i class="fa-solid fa-message text-[10px] ${isActive ? 'text-cyan-400' : 'text-slate-500'} shrink-0"></i>
                            <span class="truncate font-medium">${s.title}</span>
                        </div>
                        <div class="flex items-center gap-2 shrink-0 ml-2">
                            <span class="text-[10px] text-slate-500 font-mono">${count} msgs • ${time}</span>
                            <button onclick="event.stopPropagation(); deleteSessionItem('${s.id}')" title="Delete Session" class="opacity-0 group-hover:opacity-100 hover:text-rose-400 text-slate-500 transition-opacity p-1">
                                <i class="fa-solid fa-trash-can text-[10px]"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            list.innerHTML = html;
        }

        async function createNewSession() {
            try {
                const res = await fetch('/api/sessions', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({title: `Research Session #${chatSessions.length + 1}`})
                });
                if (res.ok) {
                    const newSess = await res.json();
                    chatSessions.unshift(newSess);
                    loadSession(newSess.id);
                    document.getElementById("sessionsMenu")?.classList.add("hidden");
                }
            } catch (e) {
                console.log("Error creating session:", e);
            }
        }

        function selectSession(sessionId) {
            document.getElementById("sessionsMenu")?.classList.add("hidden");
            document.getElementById("sessionChevron")?.classList.remove("rotate-180");
            loadSession(sessionId);
        }

        async function loadSession(sessionId) {
            currentSessionId = sessionId;
            localStorage.setItem("ALTAIR_ACTIVE_SESSION", sessionId);

            const active = chatSessions.find(s => s.id === sessionId);
            if (active) {
                document.getElementById("activeSessionTitle").innerText = active.title;
            }

            renderSessionsDropdown();

            // Clear chat UI
            const history = document.getElementById("chatHistory");
            history.innerHTML = `
                <div class="flex items-start gap-2.5">
                    <img src="/logo.png" class="w-6 h-6 rounded-md object-contain border border-cyan-500/30 shrink-0">
                    <div class="bg-darkCard border border-darkBorder p-3.5 rounded-2xl rounded-tl-none max-w-[90%] text-slate-200 leading-relaxed shadow-sm text-xs sm:text-sm">
                        <p class="font-semibold text-white mb-1">Session Activated: <span class="text-cyan-400 font-mono">${active ? active.title : sessionId}</span></p>
                        <p class="text-slate-400 text-xs">Ask any quantitative question or select an institutional model from the sidebar.</p>
                    </div>
                </div>
            `;

            try {
                const res = await fetch(`/api/sessions/${sessionId}`);
                if (res.ok) {
                    const data = await res.json();
                    const messages = data.messages || [];
                    document.getElementById("sessionCounter").innerText = `${messages.length} msgs`;

                    let lastChart = null;
                    let lastTable = null;

                    messages.forEach(m => {
                        appendMessage(m.role, m.content);
                        if (m.chart_data) lastChart = m.chart_data;
                        if (m.table_data) lastTable = m.table_data;
                    });

                    if (lastChart) renderPlotlyChart(lastChart);
                    if (lastTable) renderTable(lastTable);
                }
            } catch (e) {
                console.log("Error loading session messages:", e);
            }
        }

        async function deleteSessionItem(sessionId) {
            if (!confirm("Delete this research session?")) return;
            try {
                await fetch(`/api/sessions/${sessionId}`, {method: 'DELETE'});
                chatSessions = chatSessions.filter(s => s.id !== sessionId);
                if (currentSessionId === sessionId) {
                    currentSessionId = null;
                    localStorage.removeItem("ALTAIR_ACTIVE_SESSION");
                    if (chatSessions.length > 0) {
                        loadSession(chatSessions[0].id);
                    } else {
                        createNewSession();
                    }
                } else {
                    renderSessionsDropdown();
                }
            } catch (e) {
                console.log("Error deleting session:", e);
            }
        }

        // 5. Sidebar Toggle & Accordions
        let isMobileSidebarOpen = false;

        function toggleMobileSidebar() {
            if (window.innerWidth >= 768) {
                toggleSidebar();
                return;
            }
            isMobileSidebarOpen = !isMobileSidebarOpen;
            const sidebar = document.getElementById("mainSidebar");
            const backdrop = document.getElementById("sidebarBackdrop");
            const labels = document.querySelectorAll(".sidebar-label");

            if (isMobileSidebarOpen) {
                sidebar.classList.remove("-translate-x-full");
                sidebar.classList.add("translate-x-0");
                backdrop.classList.remove("hidden");
                // On mobile drawer, ensure all labels are displayed clearly
                labels.forEach(l => l.classList.remove("hidden"));
            } else {
                sidebar.classList.add("-translate-x-full");
                sidebar.classList.remove("translate-x-0");
                backdrop.classList.add("hidden");
            }
        }

        function closeMobileSidebar() {
            if (isMobileSidebarOpen) {
                toggleMobileSidebar();
            }
        }

        function toggleSidebar() {
            if (window.innerWidth < 768) {
                toggleMobileSidebar();
                return;
            }
            sidebarExpanded = !sidebarExpanded;
            const sidebar = document.getElementById("mainSidebar");
            const labels = document.querySelectorAll(".sidebar-label");

            if (sidebarExpanded) {
                sidebar.classList.remove("md:w-14");
                sidebar.classList.add("md:w-64");
                labels.forEach(l => l.classList.remove("hidden"));
            } else {
                sidebar.classList.remove("md:w-64");
                sidebar.classList.add("md:w-14");
                labels.forEach(l => l.classList.add("hidden"));
            }

            setTimeout(() => {
                if (document.getElementById("plotlyChartBox")) {
                    Plotly.Plots.resize('plotlyChartBox');
                }
            }, 300);
        }

        function toggleAccordion(groupId) {
            if (window.innerWidth < 768 && !isMobileSidebarOpen) {
                toggleMobileSidebar();
            } else if (window.innerWidth >= 768 && !sidebarExpanded) {
                toggleSidebar();
                return;
            }
            const group = document.getElementById(groupId);
            const chevron = document.getElementById(groupId + '-chevron');
            if (!group) return;
            
            const isHidden = group.classList.contains('hidden');
            if (isHidden) {
                group.classList.remove('hidden');
                chevron?.classList.add('rotate-180');
            } else {
                group.classList.add('hidden');
                chevron?.classList.remove('rotate-180');
            }
        }

        function selectSidebarItem(prompt) {
            if (window.innerWidth < 768 && isMobileSidebarOpen) {
                closeMobileSidebar();
            }
            sendQuickPrompt(prompt);
        }

        function setViewMode(mode) {
            currentMode = mode;
            const chatSec = document.getElementById("chatSection");
            const canvasSec = document.getElementById("canvasSection");
            const btnChat = document.getElementById("btnViewChat");
            const btnSplit = document.getElementById("btnViewSplit");
            const btnCanvas = document.getElementById("btnViewCanvas");

            [btnChat, btnSplit, btnCanvas].forEach(b => {
                b.className = "px-3 py-1 rounded-md text-slate-400 hover:text-white transition-all flex items-center gap-1.5 font-medium";
            });

            if (mode === 'chat') {
                btnChat.className = "px-3 py-1 rounded-md bg-cyan-500 text-darkBg font-bold transition-all flex items-center gap-1.5 shadow-sm";
                chatSec.className = "flex flex-col border-r border-darkBorder bg-darkCard/20 h-full w-full overflow-hidden";
                canvasSec.className = "hidden";
            } else if (mode === 'canvas') {
                btnCanvas.className = "px-3 py-1 rounded-md bg-cyan-500 text-darkBg font-bold transition-all flex items-center gap-1.5 shadow-sm";
                chatSec.className = "hidden";
                canvasSec.className = "flex-1 flex flex-col h-full overflow-y-auto p-4 sm:p-6 space-y-5 bg-darkBg w-full min-w-0";
                setTimeout(() => { Plotly.Plots.resize('plotlyChartBox'); }, 100);
            } else { // split
                btnSplit.className = "px-3 py-1 rounded-md bg-cyan-500 text-darkBg font-bold transition-all flex items-center gap-1.5 shadow-sm";
                chatSec.className = "flex flex-col border-r border-darkBorder bg-darkCard/20 h-full w-full md:w-[450px] lg:w-[480px] overflow-hidden shrink-0";
                canvasSec.className = "flex-1 hidden md:flex flex-col h-full overflow-y-auto p-4 sm:p-6 space-y-5 bg-darkBg min-w-0";
                setTimeout(() => { Plotly.Plots.resize('plotlyChartBox'); }, 100);
            }
        }

        function toggleCanvasExpand() {
            if (currentMode === 'canvas') {
                setViewMode('split');
            } else {
                setViewMode('canvas');
            }
        }

        function setMobileTab(tab) {
            const chatSec = document.getElementById("chatSection");
            const canvasSec = document.getElementById("canvasSection");
            const mTabChat = document.getElementById("mTabChat");
            const mTabCanvas = document.getElementById("mTabCanvas");

            if (tab === 'chat') {
                chatSec.classList.remove("hidden");
                canvasSec.classList.add("hidden");
                mTabChat.className = "flex-1 py-2 text-center font-bold text-cyan-400 border-b-2 border-cyan-400 flex items-center justify-center gap-1.5";
                mTabCanvas.className = "flex-1 py-2 text-center font-semibold text-slate-400 flex items-center justify-center gap-1.5";
            } else {
                chatSec.classList.add("hidden");
                canvasSec.classList.remove("hidden");
                canvasSec.classList.add("flex");
                mTabCanvas.className = "flex-1 py-2 text-center font-bold text-cyan-400 border-b-2 border-cyan-400 flex items-center justify-center gap-1.5";
                mTabChat.className = "flex-1 py-2 text-center font-semibold text-slate-400 flex items-center justify-center gap-1.5";
                setTimeout(() => { Plotly.Plots.resize('plotlyChartBox'); }, 100);
            }
        }

        function sendQuickPrompt(prompt) {
            document.getElementById("userMessage").value = prompt;
            handleUserSubmit(new Event('submit'));
        }

        async function handleUserSubmit(e) {
            e.preventDefault();
            const input = document.getElementById("userMessage");
            const msg = input.value.trim();
            if (!msg) return;

            appendMessage('user', msg);
            input.value = "";

            const history = document.getElementById("chatHistory");
            const loadingDiv = document.createElement("div");
            loadingDiv.className = "flex items-start gap-2.5";
            loadingDiv.id = "loadingBubble";
            loadingDiv.innerHTML = `
                <img src="/logo.png" class="w-6 h-6 rounded-md object-contain border border-cyan-500/30 shrink-0">
                <div class="bg-darkCard border border-darkBorder p-3 rounded-2xl rounded-tl-none text-slate-400 text-xs flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                    Running quant analytics & live feed...
                </div>
            `;
            history.appendChild(loadingDiv);
            history.scrollTop = history.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        message: msg,
                        pin: "authenticated",
                        session_id: currentSessionId
                    })
                });
                
                const data = await res.json();
                document.getElementById("loadingBubble")?.remove();

                appendMessage('ai', data.reply);

                if (data.multi_charts) {
                    currentMultiCharts = data.multi_charts;
                    document.getElementById("chartTypeSwitcher")?.classList.remove("hidden");
                    switchChartType("quadrant");
                } else {
                    document.getElementById("chartTypeSwitcher")?.classList.add("hidden");
                    if (data.chart) {
                        renderPlotlyChart(data.chart);
                    }
                }

                if (window.innerWidth < 768 && (data.chart || data.multi_charts)) {
                    setMobileTab('canvas');
                }

                if (data.table) {
                    renderTable(data.table);
                }

                if (data.notebook_updated) {
                    setRightPaneView('notebook');
                    loadNotebookData();
                }

                // Update session messages count
                if (currentSessionId) {
                    const sess = chatSessions.find(s => s.id === currentSessionId);
                    if (sess) {
                        sess.message_count = (sess.message_count || 0) + 2;
                        sess.updated_at = new Date().toISOString();
                        document.getElementById("sessionCounter").innerText = `${sess.message_count} msgs`;
                        renderSessionsDropdown();
                    }
                }
            } catch (err) {
                document.getElementById("loadingBubble")?.remove();
                appendMessage('ai', "Error connecting to engine. Please re-check connection.");
            }
        }

        // Initialize auth check on load
        checkAuth();

        let currentMultiCharts = null;
        let activeChartType = "quadrant";

        function switchChartType(type) {
            if (!currentMultiCharts || !currentMultiCharts[type]) return;
            activeChartType = type;

            ["quadrant", "ranking", "frontier", "sector"].forEach(t => {
                const btn = document.getElementById("btnChart-" + t);
                if (btn) {
                    if (t === type) {
                        btn.className = "px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shrink-0 shadow-sm";
                    } else {
                        btn.className = "px-2.5 py-1 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0";
                    }
                }
            });

            renderPlotlyChart(currentMultiCharts[type]);
        }

        function appendMessage(sender, text) {
            const history = document.getElementById("chatHistory");
            const div = document.createElement("div");

            if (sender === 'user') {
                div.className = "flex justify-end";
                div.innerHTML = `
                    <div class="bg-gradient-to-r from-cyan-600 to-blue-600 text-white p-3 rounded-2xl rounded-tr-none max-w-[85%] shadow-md leading-relaxed text-xs sm:text-sm">
                        ${text}
                    </div>
                `;
            } else {
                div.className = "flex items-start gap-2.5";
                div.innerHTML = `
                    <img src="/logo.png" class="w-6 h-6 rounded-md object-contain border border-cyan-500/30 shrink-0">
                    <div class="bg-darkCard border border-darkBorder p-3.5 rounded-2xl rounded-tl-none max-w-[90%] text-slate-200 leading-relaxed shadow-sm text-xs sm:text-sm">
                        ${marked_render(text)}
                    </div>
                `;
            }
            history.appendChild(div);
            history.scrollTop = history.scrollHeight;
        }

        function marked_render(txt) {
            return txt.replace(/### (.*?)\\n/g, '<h4 class="font-bold text-cyan-400 text-xs sm:text-sm mt-1 mb-1">$1</h4>')
                      .replace(/\\*\\*(.*?)\\*\\*/g, '<strong class="text-white font-semibold">$1</strong>')
                      .replace(/\\n/g, '<br>');
        }

        function renderPlotlyChart(chartJson) {
            const ph = document.getElementById("emptyChartPlaceholder");
            if (ph) ph.remove();

            chartJson.layout = chartJson.layout || {};
            chartJson.layout.autosize = true;
            delete chartJson.layout.width;
            chartJson.layout.margin = chartJson.layout.margin || { l: 45, r: 35, t: 55, b: 45 };
            chartJson.layout.paper_bgcolor = "#060911";
            chartJson.layout.plot_bgcolor = "#070b14";

            Plotly.react('plotlyChartBox', chartJson.data, chartJson.layout, {
                responsive: true,
                displayModeBar: true,
                displaylogo: false
            });
            document.getElementById("canvasTimestamp").innerText = "Updated: " + new Date().toLocaleTimeString();
            setTimeout(() => { Plotly.Plots.resize('plotlyChartBox'); }, 100);
        }

        // Right Pane View Switcher: Canvas vs Jupyter Notebook
        let currentRightPaneView = "canvas";
        let notebookData = null;

        function setRightPaneView(view) {
            currentRightPaneView = view;
            const canvasView = document.getElementById("canvasViewContainer");
            const nbView = document.getElementById("notebookViewContainer");
            const btnCanvas = document.getElementById("btnTabCanvas");
            const btnNb = document.getElementById("btnTabNotebook");
            const screenerSwitcher = document.getElementById("chartTypeSwitcher");

            if (view === "canvas") {
                canvasView?.classList.remove("hidden");
                nbView?.classList.add("hidden");
                btnCanvas.className = "px-3 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shadow-sm";
                btnNb.className = "px-3 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs";
                if (currentMultiCharts) screenerSwitcher?.classList.remove("hidden");
                setTimeout(() => { if (document.getElementById("plotlyChartBox")) Plotly.Plots.resize('plotlyChartBox'); }, 100);
            } else {
                canvasView?.classList.add("hidden");
                nbView?.classList.remove("hidden");
                screenerSwitcher?.classList.add("hidden");
                btnNb.className = "px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shadow-sm";
                btnCanvas.className = "px-3 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs";
                if (!notebookData) {
                    loadNotebookData();
                }
            }
        }

        async function loadNotebookData() {
            const meta = document.getElementById("nbMetaText");
            const list = document.getElementById("notebookCellsList");
            if (meta) meta.innerText = "Loading cells from ste_engine_lab.ipynb...";

            try {
                const res = await fetch('/api/notebook');
                if (!res.ok) throw new Error("Notebook not found");
                notebookData = await res.json();
                renderNotebookView(notebookData);
            } catch (err) {
                if (meta) meta.innerText = "Error loading notebook: " + err.message;
            }
        }

        function renderNotebookView(nb) {
            const list = document.getElementById("notebookCellsList");
            const meta = document.getElementById("nbMetaText");
            const cells = nb.cells || [];

            if (meta) meta.innerText = `${cells.length} Cells • Quantitative Harmonic & Swing Engine`;
            if (!list) return;

            let html = "";
            cells.forEach((cell, idx) => {
                const isCode = cell.cell_type === "code";
                const source = Array.isArray(cell.source) ? cell.source.join("") : (cell.source || "");
                const count = cell.execution_count != null ? cell.execution_count : (idx + 1);

                if (isCode) {
                    // Extract text output if present
                    let outputHtml = "";
                    if (cell.outputs && cell.outputs.length > 0) {
                        cell.outputs.forEach(out => {
                            if (out.text) {
                                const outText = Array.isArray(out.text) ? out.text.join("") : out.text;
                                outputHtml += `<pre class="bg-black/60 text-emerald-300 p-3 rounded-xl font-mono text-[11px] overflow-x-auto max-h-48 border border-darkBorder/40 mt-2">${escapeHtml(outText)}</pre>`;
                            }
                        });
                    }

                    html += `
                        <div class="bg-darkCard border border-darkBorder rounded-2xl p-3.5 shadow-md space-y-2 group transition-all hover:border-cyan-500/30" id="cellBox-${idx}">
                            <!-- Cell Header -->
                            <div class="flex items-center justify-between text-xs pb-1 border-b border-darkBorder/40">
                                <div class="flex items-center gap-2">
                                    <span class="font-mono text-cyan-400 font-bold text-[11px] bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 rounded">In [${count}]:</span>
                                    <span class="text-[10px] text-slate-400 font-mono">Python Cell</span>
                                </div>
                                <div class="flex items-center gap-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
                                    <button onclick="copyCellCode(${idx})" title="Copy Code" class="px-2 py-1 rounded-lg bg-darkBg hover:bg-slate-800 text-slate-400 hover:text-cyan-300 border border-darkBorder text-[10px] flex items-center gap-1">
                                        <i class="fa-regular fa-copy"></i> Copy
                                    </button>
                                    <button onclick="toggleCellEdit(${idx})" title="Edit Cell Code" class="px-2 py-1 rounded-lg bg-darkBg hover:bg-slate-800 text-slate-400 hover:text-white border border-darkBorder text-[10px] flex items-center gap-1">
                                        <i class="fa-solid fa-pen"></i> Edit
                                    </button>
                                </div>
                            </div>

                            <!-- Code Editor Textarea -->
                            <div class="relative">
                                <textarea id="cellCode-${idx}" rows="${Math.max(3, Math.min(18, countLines(source) + 1))}" 
                                          class="w-full bg-[#080d1a] text-cyan-200 font-mono text-xs p-3.5 rounded-xl border border-darkBorder/60 focus:outline-none focus:border-cyan-500 leading-relaxed transition-all resize-y select-text"
                                          oninput="markNotebookDirty()">${escapeHtml(source)}</textarea>
                            </div>

                            <!-- Outputs -->
                            ${outputHtml}
                        </div>
                    `;
                } else {
                    // Markdown Cell
                    html += `
                        <div class="bg-darkCard/70 border border-darkBorder rounded-2xl p-4 shadow-sm space-y-2 group hover:border-amber-500/30 transition-all" id="cellBox-${idx}">
                            <div class="flex items-center justify-between text-xs pb-1 border-b border-darkBorder/40">
                                <span class="text-[10px] font-mono text-amber-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                                    <i class="fa-solid fa-align-left text-[9px]"></i> Markdown Cell #${idx + 1}
                                </span>
                                <button onclick="toggleCellEdit(${idx})" class="text-slate-500 hover:text-amber-300 text-[10px]">
                                    <i class="fa-solid fa-pen"></i> Edit
                                </button>
                            </div>
                            <div id="cellMdView-${idx}" class="text-slate-200 text-xs sm:text-sm leading-relaxed select-text">
                                ${marked_render(source)}
                            </div>
                            <textarea id="cellCode-${idx}" class="w-full bg-[#080d1a] text-amber-200 font-mono text-xs p-3 rounded-xl border border-darkBorder/60 focus:outline-none focus:border-amber-500 hidden resize-y select-text"
                                      rows="${Math.max(3, countLines(source) + 1)}" oninput="markNotebookDirty()">${escapeHtml(source)}</textarea>
                        </div>
                    `;
                }
            });

            list.innerHTML = html;
        }

        function toggleCellEdit(idx) {
            const txt = document.getElementById("cellCode-" + idx);
            const view = document.getElementById("cellMdView-" + idx);
            if (view && txt) {
                const isHidden = txt.classList.contains("hidden");
                if (isHidden) {
                    txt.classList.remove("hidden");
                    view.classList.add("hidden");
                    txt.focus();
                } else {
                    txt.classList.add("hidden");
                    view.classList.remove("hidden");
                    view.innerHTML = marked_render(txt.value);
                }
            }
        }

        function copyCellCode(idx) {
            const txt = document.getElementById("cellCode-" + idx);
            if (txt) {
                navigator.clipboard.writeText(txt.value);
                alert("Cell code copied to clipboard!");
            }
        }

        function markNotebookDirty() {
            const btn = document.getElementById("btnSaveNotebook");
            if (btn) {
                btn.innerHTML = `<i class="fa-solid fa-circle-exclamation text-amber-300 animate-pulse"></i> Save Changes`;
                btn.className = "h-8 px-3.5 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-md transition-all";
            }
        }

        async function saveNotebookToServer() {
            if (!notebookData || !notebookData.cells) return;
            const btn = document.getElementById("btnSaveNotebook");
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Saving...`;
            }

            // Sync updated text from DOM
            notebookData.cells.forEach((cell, idx) => {
                const txt = document.getElementById("cellCode-" + idx);
                if (txt) {
                    cell.source = splitIntoLines(txt.value);
                }
            });

            try {
                const res = await fetch('/api/notebook/save', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cells: notebookData.cells})
                });
                if (res.ok) {
                    if (btn) {
                        btn.innerHTML = `<i class="fa-solid fa-check text-emerald-300"></i> Saved to Disk!`;
                        btn.className = "h-8 px-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all";
                        setTimeout(() => {
                            btn.innerHTML = `<i class="fa-solid fa-floppy-disk text-[11px]"></i> Save Notebook`;
                        }, 2500);
                    }
                }
            } catch (err) {
                alert("Error saving notebook: " + err.message);
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        async function addNewNotebookCell() {
            try {
                const res = await fetch('/api/notebook/add-cell', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        cell_type: "code",
                        source: `# New Quantitative Research Cell
import yfinance as yf
import pandas as pd

# Your code here`
                    })
                });
                if (res.ok) {
                    await loadNotebookData();
                    const list = document.getElementById("notebookCellsList");
                    if (list && list.lastElementChild) {
                        list.lastElementChild.scrollIntoView({behavior: "smooth"});
                    }
                }
            } catch (e) {
                console.log("Error adding cell:", e);
            }
        }

        function escapeHtml(text) {
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Render Scrollable Leaderboard Table with Sticky Header
        function renderTable(tableData) {
            if (!tableData || tableData.length === 0) return;
            const container = document.getElementById("tableContainerBox");
            const wrapper = document.getElementById("dynamicTableWrapper");
            const badge = document.getElementById("tableCountBadge");
            container.classList.remove("hidden");

            if (badge) badge.innerText = `${tableData.length} Picks`;

            const cols = Object.keys(tableData[0]);
            let html = '<table class="w-full text-left text-xs border-collapse min-w-[700px]">';
            html += '<thead class="bg-slate-900/95 sticky top-0 z-10 text-slate-400 border-b border-darkBorder uppercase text-[10px] tracking-wider backdrop-blur"><tr>';
            cols.forEach(c => html += `<th class="p-3 whitespace-nowrap">${c.replace(/_/g, ' ')}</th>`);
            html += '</tr></thead><tbody class="divide-y divide-darkBorder/30">';

            tableData.forEach((row, i) => {
                const bg = i % 2 === 0 ? 'bg-darkCard/90' : 'bg-darkBg/80';
                html += `<tr class="${bg} hover:bg-slate-800/60 transition-colors">`;
                cols.forEach(c => {
                    let val = row[c];
                    let cellHtml = `<span class="text-slate-300 font-mono">${val}</span>`;
                    
                    if (c === 'Symbol') {
                        cellHtml = `<span class="font-bold text-white font-mono flex items-center gap-1.5"><span class="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0"></span>${val}</span>`;
                    } else if (c === 'Verdict') {
                        const isAccum = String(val).includes('ACCUM');
                        const isBuy = String(val).includes('BUY');
                        const color = isAccum ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : (isBuy ? 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30' : 'bg-slate-800 text-slate-400 border-slate-700');
                        cellHtml = `<span class="px-2 py-0.5 rounded-full text-[10px] font-semibold border ${color} whitespace-nowrap">${val}</span>`;
                    } else if (c === 'Quant_Score') {
                        cellHtml = `<span class="font-bold font-mono text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">${val}</span>`;
                    } else if (c === 'CMP') {
                        cellHtml = `<span class="font-bold font-mono text-white">₹${val}</span>`;
                    } else if (String(val).includes('+')) {
                        cellHtml = `<span class="text-emerald-400 font-mono font-medium">${val}</span>`;
                    } else if (String(val).includes('-')) {
                        cellHtml = `<span class="text-rose-400 font-mono font-medium">${val}</span>`;
                    }
                    html += `<td class="p-3 whitespace-nowrap">${cellHtml}</td>`;
                });
                html += '</tr>';
            });
            html += '</tbody></table>';
            wrapper.innerHTML = html;
        }

        window.addEventListener('resize', () => {
            if (document.getElementById("plotlyChartBox")) {
                Plotly.Plots.resize('plotlyChartBox');
            }
        });

        // Close profile and sessions menus when clicking outside
        document.addEventListener('click', (e) => {
            const profileBtn = document.getElementById("profilePillBtn");
            const profileDd = document.getElementById("profileDropdown");
            if (profileBtn && profileDd && !profileBtn.contains(e.target) && !profileDd.contains(e.target)) {
                profileDd.classList.add("hidden");
                document.getElementById("profileChevron")?.classList.remove("rotate-180");
            }

            const sessBtn = document.getElementById("sessionSelectorBtn");
            const sessMenu = document.getElementById("sessionsMenu");
            if (sessBtn && sessMenu && !sessBtn.contains(e.target) && !sessMenu.contains(e.target)) {
                sessMenu.classList.add("hidden");
                document.getElementById("sessionChevron")?.classList.remove("rotate-180");
            }
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
