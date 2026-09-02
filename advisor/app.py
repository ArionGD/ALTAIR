import os
import sys
import io
import csv
import json
from datetime import datetime
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Ensure parent directory in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from advisor.sectors import get_all_sectors, get_sector_tickers
from advisor.engine import run_advisor_scan

app = FastAPI(title="ALTAIR Advisor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGO_PATH = os.path.join(PARENT_DIR, "Garud_Quant-lab_logo.png")

@app.get("/logo.png")
def get_logo():
    if os.path.exists(LOGO_PATH):
        return FileResponse(LOGO_PATH)
    alt_logo = os.path.join(PARENT_DIR, "Altair Logo.png")
    if os.path.exists(alt_logo):
        return FileResponse(alt_logo)
    return Response(status_code=404)

@app.get("/api/sectors")
def api_get_sectors():
    return {"sectors": get_all_sectors()}

@app.get("/api/scan")
def api_scan_sector(sector: str = Query("Pharma & Healthcare"), include_gann: bool = Query(False)):
    try:
        data = run_advisor_scan(sector_name=sector, include_gann=include_gann)
        
        # Calculate summary KPI stats
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
            "sector": sector,
            "include_gann": include_gann,
            "kpis": kpis,
            "rankings": rankings,
            "charts": data.get("charts", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/export")
def api_export_csv(sector: str = Query("Pharma & Healthcare"), include_gann: bool = Query(False)):
    try:
        data = run_advisor_scan(sector_name=sector, include_gann=include_gann)
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
        filename = f"altair_advisor_{sector.replace(' ', '_').lower()}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def serve_advisor_dashboard():
    html_content = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ALTAIR Advisor | Institutional Sector & Bi-Directional Alpha Terminal</title>
    <link rel="icon" type="image/png" href="/logo.png">

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        darkBg: '#060911',
                        darkCard: '#0a101f',
                        darkBorder: '#1e293b'
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
                    }
                }
            }
        }
    </script>

    <!-- FontAwesome & Plotly -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>

    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #060911; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body class="bg-darkBg text-slate-100 font-sans min-h-screen flex flex-col select-none">

    <!-- Top Navigation Header -->
    <header class="bg-darkCard/90 backdrop-blur border-b border-darkBorder px-4 sm:px-6 py-3 flex items-center justify-between shrink-0 sticky top-0 z-30 shadow-md">
        <div class="flex items-center space-x-3.5">
            <img src="/logo.png" alt="Altair Logo" class="w-9 h-9 rounded-xl object-contain border border-cyan-500/30 shadow-lg shadow-cyan-500/10">
            <div>
                <div class="flex items-center gap-2">
                    <h1 class="font-black text-sm sm:text-base text-white tracking-wider">ALTAIR <span class="text-cyan-400 font-mono text-xs font-semibold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">ADVISOR</span></h1>
                    <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Production Feed
                    </span>
                </div>
                <p class="text-[10px] sm:text-[11px] text-slate-400 font-medium">advisor.altair-engine.com • Top 20 Sector Intelligence & Bi-Directional Alpha</p>
            </div>
        </div>

        <div class="flex items-center gap-3">
            <a href="http://127.0.0.1:8080" target="_blank" title="Open Quant Lab Prototype Workbench" class="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 hover:text-cyan-300 text-xs transition-all font-medium">
                <i class="fa-solid fa-flask-vial text-cyan-400 text-xs"></i> Quant Lab Workbench
            </a>
            <div class="text-right hidden md:block">
                <div class="text-xs font-mono text-white font-bold" id="liveClock">--:--:--</div>
                <div class="text-[10px] text-slate-500 font-mono">NSE Live Feed Active</div>
            </div>
        </div>
    </header>

    <!-- Main Single-Page Workspace Container -->
    <main class="flex-1 p-4 sm:p-6 max-w-7xl mx-auto w-full space-y-5">

        <!-- Controls Bar: Sector Selector + Gann Toggle -->
        <section class="bg-darkCard border border-darkBorder rounded-2xl p-4 sm:p-5 shadow-xl space-y-4">
            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                
                <!-- Sector Dropdown & Title -->
                <div class="flex flex-col sm:flex-row sm:items-center gap-3">
                    <div>
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">Target Sector Preference</span>
                        <div class="relative min-w-[240px]">
                            <select id="sectorSelect" onchange="onSectorSelectChange(this.value)" 
                                    class="w-full appearance-none bg-darkBg border border-cyan-500/40 text-cyan-300 text-xs sm:text-sm font-bold rounded-xl px-3.5 py-2.5 pr-8 focus:outline-none focus:border-cyan-400 cursor-pointer shadow-sm">
                                <option value="Pharma & Healthcare">💊 Pharma & Healthcare (Top 20)</option>
                                <option value="Banking - Private">🏦 Banking - Private (Top 20)</option>
                                <option value="Banking - PSU">🏛️ Banking - PSU (Top 12)</option>
                                <option value="IT & Technology">💻 IT & Technology (Top 20)</option>
                                <option value="Automobiles & Ancillaries">🚗 Automobiles & Ancillaries (Top 20)</option>
                                <option value="Consumer Goods (FMCG)">🛒 Consumer Goods - FMCG (Top 20)</option>
                                <option value="Energy, Oil & Utilities">⚡ Energy, Oil & Utilities (Top 20)</option>
                                <option value="Metals & Mining">⛏️ Metals & Mining (Top 20)</option>
                                <option value="Industrials & Defense">🛡️ Industrials & Defense (Top 20)</option>
                                <option value="Real Estate & Infra">🏢 Real Estate & Infra (Top 20)</option>
                            </select>
                            <i class="fa-solid fa-chevron-down absolute right-3 top-3 text-cyan-400 pointer-events-none text-xs"></i>
                        </div>
                    </div>

                    <!-- Gann Proximity Weight Switcher -->
                    <div class="sm:border-l sm:border-darkBorder sm:pl-4">
                        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">🔮 W.D. Gann Cycle Resonance</span>
                        <button onclick="toggleGannScoring()" id="btnGannToggle" 
                                class="px-3 py-2 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer">
                            <span id="gannDot" class="w-2 h-2 rounded-full bg-slate-600"></span>
                            <span id="gannLabel">Gann Score: OFF (Fundamental DCF & Momentum Only)</span>
                        </button>
                    </div>
                </div>

                <!-- Action Utilities: Refresh & Export -->
                <div class="flex items-center gap-2 shrink-0">
                    <button onclick="refreshData()" title="Refresh Sector Data" class="h-9 px-3.5 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-all">
                        <i class="fa-solid fa-rotate text-cyan-400 text-xs"></i> Refresh
                    </button>
                    <button onclick="exportToCsv()" title="Export Sector Scorecard as CSV" class="h-9 px-3.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all">
                        <i class="fa-solid fa-file-csv text-xs"></i> Export CSV
                    </button>
                </div>
            </div>

            <!-- Horizontal Sector Quick Chips Bar -->
            <div class="pt-2 border-t border-darkBorder/60 flex items-center gap-2 overflow-x-auto pb-1 text-xs" id="quickChipsBar">
                <!-- Populated dynamically by JS -->
            </div>
        </section>

        <!-- KPI Summary Cards Row -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" id="kpiCardsContainer">
            <!-- 1. Sector Average Margin of Safety -->
            <div class="bg-darkCard border border-darkBorder rounded-2xl p-4 shadow-lg flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Sector Valuation Delta</span>
                    <h3 class="text-xl sm:text-2xl font-black text-white mt-1 font-mono" id="kpiAvgMoS">--%</h3>
                    <p class="text-[10px] text-slate-400 mt-0.5" id="kpiAvgMoSSub">Mean DCF Margin of Safety</p>
                </div>
                <div class="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 text-lg shrink-0">
                    <i class="fa-solid fa-scale-balanced"></i>
                </div>
            </div>

            <!-- 2. Top Ranked Long Opportunity -->
            <div class="bg-darkCard border border-darkBorder rounded-2xl p-4 shadow-lg flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-wider block">Top Swing Long Pick</span>
                    <h3 class="text-xl sm:text-2xl font-black text-white mt-1 font-mono" id="kpiTopLongSymbol">--</h3>
                    <p class="text-[10px] text-slate-400 mt-0.5" id="kpiTopLongDetails">Target: -- • MoS: --</p>
                </div>
                <div class="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg shrink-0">
                    <i class="fa-solid fa-arrow-trend-up"></i>
                </div>
            </div>

            <!-- 3. Top Ranked Short Opportunity -->
            <div class="bg-darkCard border border-darkBorder rounded-2xl p-4 shadow-lg flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-bold text-rose-400 uppercase tracking-wider block">Prime Short / Hedge Candidate</span>
                    <h3 class="text-xl sm:text-2xl font-black text-white mt-1 font-mono" id="kpiTopShortSymbol">--</h3>
                    <p class="text-[10px] text-slate-400 mt-0.5" id="kpiTopShortDetails">Floor: -- • MoS: --</p>
                </div>
                <div class="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 text-lg shrink-0">
                    <i class="fa-solid fa-arrow-trend-down"></i>
                </div>
            </div>

            <!-- 4. Sector Breadth & Setup Count -->
            <div class="bg-darkCard border border-darkBorder rounded-2xl p-4 shadow-lg flex items-center justify-between">
                <div>
                    <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Setup Breakdown</span>
                    <div class="flex items-center gap-3 mt-1 font-mono text-base font-bold">
                        <span class="text-emerald-400" id="kpiLongCount">0 Longs</span>
                        <span class="text-slate-600">/</span>
                        <span class="text-rose-400" id="kpiShortCount">0 Shorts</span>
                    </div>
                    <p class="text-[10px] text-slate-400 mt-0.5">Top 20 Liquid Candidates</p>
                </div>
                <div class="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 text-lg shrink-0">
                    <i class="fa-solid fa-chart-pie"></i>
                </div>
            </div>
        </section>

        <!-- Visual Charts Suite (Plotly Dark Theme) -->
        <section class="bg-darkCard border border-darkBorder rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-darkBorder/70 pb-3">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-chart-column text-cyan-400"></i>
                    <h2 class="text-xs sm:text-sm font-bold text-white uppercase tracking-wider" id="chartSectionTitle">Valuation & Risk Channel Visualizer</h2>
                </div>

                <!-- 3 Simple Chart View Switcher Buttons -->
                <div class="flex items-center bg-darkBg border border-darkBorder rounded-xl p-1 text-xs gap-1 select-none overflow-x-auto">
                    <button onclick="switchChartTab('dcf')" id="btnChartDcf" class="px-2.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shrink-0 shadow-sm">
                        <i class="fa-solid fa-scale-balanced text-[11px]"></i> DCF Fair Value vs CMP
                    </button>
                    <button onclick="switchChartTab('matrix')" id="btnChartMatrix" class="px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0">
                        <i class="fa-solid fa-crosshairs text-[11px]"></i> Opportunity Matrix
                    </button>
                    <button onclick="switchChartTab('brackets')" id="btnChartBrackets" class="px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0">
                        <i class="fa-solid fa-arrows-left-right-to-line text-[11px]"></i> S1 / R1 Brackets
                    </button>
                </div>
            </div>

            <!-- Plotly Container -->
            <div class="w-full min-h-[440px] relative overflow-hidden rounded-xl bg-darkBg/50 p-2">
                <div id="advisorPlotlyBox" class="w-full h-full min-h-[420px]">
                    <div class="flex flex-col items-center justify-center h-full min-h-[380px] text-slate-500" id="chartLoading">
                        <i class="fa-solid fa-spinner animate-spin text-3xl mb-2 text-cyan-400"></i>
                        <p class="text-xs">Computing DCF intrinsic values, S1/R1 pivots & rankings...</p>
                    </div>
                </div>
            </div>
        </section>

        <!-- Ranked Opportunity Scorecard Table -->
        <section class="bg-darkCard border border-darkBorder rounded-2xl p-4 sm:p-6 shadow-xl space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-darkBorder/70 pb-3">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-list-ol text-cyan-400"></i>
                    <h2 class="text-xs sm:text-sm font-bold text-white uppercase tracking-wider">Top 20 Ranked Sector Scorecard</h2>
                    <span id="scorecardSectorBadge" class="text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-full font-mono">Pharma</span>
                </div>

                <!-- Table Filter Pills: All / Longs / Shorts -->
                <div class="flex items-center gap-2">
                    <div class="flex items-center bg-darkBg border border-darkBorder rounded-xl p-1 text-xs gap-1">
                        <button onclick="filterTable('ALL')" id="filterBtnAll" class="px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 text-xs transition-all">All (20)</button>
                        <button onclick="filterTable('LONG')" id="filterBtnLong" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-emerald-400 font-medium text-xs transition-all flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Longs
                        </button>
                        <button onclick="filterTable('SHORT')" id="filterBtnShort" class="px-2.5 py-1 rounded-lg text-slate-400 hover:text-rose-400 font-medium text-xs transition-all flex items-center gap-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span> Shorts
                        </button>
                    </div>
                    <input type="text" id="tableSearchInput" oninput="onSearchInput(this.value)" placeholder="Search ticker..." 
                           class="bg-darkBg border border-darkBorder rounded-xl px-3 py-1 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-32 sm:w-44">
                </div>
            </div>

            <!-- Scrollable Responsive Table -->
            <div class="overflow-x-auto overflow-y-auto max-h-[500px] w-full border border-darkBorder/60 rounded-xl bg-darkBg/60">
                <table class="w-full text-left text-xs border-collapse min-w-[850px]">
                    <thead class="bg-slate-900/95 sticky top-0 z-10 text-slate-400 border-b border-darkBorder uppercase text-[10px] tracking-wider backdrop-blur">
                        <tr>
                            <th class="p-3 whitespace-nowrap">Rank</th>
                            <th class="p-3 whitespace-nowrap">Company</th>
                            <th class="p-3 whitespace-nowrap">CMP (₹)</th>
                            <th class="p-3 whitespace-nowrap">Action Signal</th>
                            <th class="p-3 whitespace-nowrap">Score</th>
                            <th class="p-3 whitespace-nowrap">DCF Value</th>
                            <th class="p-3 whitespace-nowrap">Margin of Safety</th>
                            <th class="p-3 whitespace-nowrap">P/E</th>
                            <th class="p-3 whitespace-nowrap">14D RSI</th>
                            <th class="p-3 whitespace-nowrap">Floor (S1)</th>
                            <th class="p-3 whitespace-nowrap">Target (R1)</th>
                            <th class="p-3 whitespace-nowrap">R/R</th>
                        </tr>
                    </thead>
                    <tbody id="advisorTableBody" class="divide-y divide-darkBorder/30">
                        <!-- Rows rendered dynamically by JS -->
                    </tbody>
                </table>
            </div>
            <p class="text-[11px] text-slate-500 text-right font-mono">Institutional Decision Engine • S1 Floor & R1 Ceiling Based on Camarilla Structural High/Lows</p>
        </section>

    </main>

    <!-- Footer -->
    <footer class="border-t border-darkBorder/50 py-3 px-6 text-center text-xs text-slate-500 font-mono mt-8">
        ALTAIR Advisor Terminal • advisor.altair-engine.com • Proprietary Quantitative Risk Infrastructure
    </footer>

    <!-- Client-side JavaScript -->
    <script>
        let currentSector = "Pharma & Healthcare";
        let isGannEnabled = false;
        let activeChartTab = "dcf";
        let currentFilter = "ALL";
        let rawRankings = [];
        let currentCharts = {};

        const SECTORS_LIST = [
            { id: "Pharma & Healthcare", label: "Pharma", icon: "💊" },
            { id: "Banking - Private", label: "Pvt Banks", icon: "🏦" },
            { id: "Banking - PSU", label: "PSU Banks", icon: "🏛️" },
            { id: "IT & Technology", label: "IT & Tech", icon: "💻" },
            { id: "Automobiles & Ancillaries", label: "Auto", icon: "🚗" },
            { id: "Consumer Goods (FMCG)", label: "FMCG", icon: "🛒" },
            { id: "Energy, Oil & Utilities", label: "Energy", icon: "⚡" },
            { id: "Metals & Mining", label: "Metals", icon: "⛏️" },
            { id: "Industrials & Defense", label: "Defense", icon: "🛡️" },
            { id: "Real Estate & Infra", label: "Realty", icon: "🏢" }
        ];

        // 1. Initialize Dashboard
        window.addEventListener("DOMContentLoaded", () => {
            renderQuickChips();
            updateLiveClock();
            setInterval(updateLiveClock, 1000);
            loadSectorData(currentSector, isGannEnabled);
        });

        function updateLiveClock() {
            const now = new Date();
            const clock = document.getElementById("liveClock");
            if (clock) clock.innerText = now.toLocaleTimeString();
        }

        function renderQuickChips() {
            const bar = document.getElementById("quickChipsBar");
            if (!bar) return;
            let html = "";
            SECTORS_LIST.forEach(s => {
                const isActive = s.id === currentSector;
                const activeClass = isActive 
                    ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/50 font-bold shadow-sm" 
                    : "bg-darkBg hover:bg-slate-800 text-slate-400 hover:text-white border-darkBorder";
                html += `
                    <button onclick="onSectorSelectChange('${s.id}')" 
                            class="px-2.5 py-1 rounded-lg border ${activeClass} transition-all shrink-0 flex items-center gap-1.5">
                        <span>${s.icon}</span> <span>${s.label}</span>
                    </button>
                `;
            });
            bar.innerHTML = html;
        }

        function onSectorSelectChange(sec) {
            currentSector = sec;
            const select = document.getElementById("sectorSelect");
            if (select) select.value = sec;
            renderQuickChips();
            loadSectorData(currentSector, isGannEnabled);
        }

        function toggleGannScoring() {
            isGannEnabled = !isGannEnabled;
            const btn = document.getElementById("btnGannToggle");
            const dot = document.getElementById("gannDot");
            const lbl = document.getElementById("gannLabel");

            if (isGannEnabled) {
                btn.className = "px-3 py-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-2 transition-all cursor-pointer shadow-sm";
                dot.className = "w-2 h-2 rounded-full bg-amber-400 animate-pulse";
                lbl.innerText = "Gann Score: ON (Harmonics Boost Active)";
            } else {
                btn.className = "px-3 py-2 rounded-xl bg-darkBg hover:bg-slate-800 border border-darkBorder text-slate-300 text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer";
                dot.className = "w-2 h-2 rounded-full bg-slate-600";
                lbl.innerText = "Gann Score: OFF (Fundamental DCF & Momentum Only)";
            }
            loadSectorData(currentSector, isGannEnabled);
        }

        async function loadSectorData(sector, includeGann) {
            const badge = document.getElementById("scorecardSectorBadge");
            if (badge) badge.innerText = sector;

            const tableBody = document.getElementById("advisorTableBody");
            if (tableBody) {
                tableBody.innerHTML = `<tr><td colspan="12" class="p-8 text-center text-slate-400"><i class="fa-solid fa-spinner animate-spin text-lg mr-2 text-cyan-400"></i> Calculating DCF, S1/R1, and rankings for ${sector}...</td></tr>`;
            }

            try {
                const res = await fetch(`/api/scan?sector=${encodeURIComponent(sector)}&include_gann=${includeGann}`);
                if (!res.ok) throw new Error("Error loading sector scan");
                const data = await res.json();

                rawRankings = data.rankings || [];
                currentCharts = data.charts || {};

                updateKPIs(data.kpis);
                renderTableRows(rawRankings);
                renderActiveChart();
            } catch (err) {
                console.error(err);
                if (tableBody) {
                    tableBody.innerHTML = `<tr><td colspan="12" class="p-6 text-center text-rose-400">Error connecting to Advisor engine. Please retry.</td></tr>`;
                }
            }
        }

        function updateKPIs(kpis) {
            if (!kpis) return;
            const mosEl = document.getElementById("kpiAvgMoS");
            if (mosEl) {
                const val = kpis.avg_margin_of_safety || 0;
                mosEl.innerText = (val > 0 ? "+" : "") + val + "%";
                mosEl.className = "text-xl sm:text-2xl font-black mt-1 font-mono " + (val >= 0 ? "text-emerald-400" : "text-rose-400");
            }

            const longSym = document.getElementById("kpiTopLongSymbol");
            const longDet = document.getElementById("kpiTopLongDetails");
            if (kpis.top_long) {
                if (longSym) longSym.innerText = kpis.top_long.symbol;
                if (longDet) longDet.innerText = `Target: ₹${kpis.top_long.r1_resistance} • MoS: +${kpis.top_long.margin_of_safety_pct}%`;
            } else {
                if (longSym) longSym.innerText = "None";
                if (longDet) longDet.innerText = "No strong long setup";
            }

            const shortSym = document.getElementById("kpiTopShortSymbol");
            const shortDet = document.getElementById("kpiTopShortDetails");
            if (kpis.top_short) {
                if (shortSym) shortSym.innerText = kpis.top_short.symbol;
                if (shortDet) shortDet.innerText = `Floor: ₹${kpis.top_short.s1_support} • MoS: ${kpis.top_short.margin_of_safety_pct}%`;
            } else {
                if (shortSym) shortSym.innerText = "None";
                if (shortDet) shortDet.innerText = "No short candidate";
            }

            const lCount = document.getElementById("kpiLongCount");
            const sCount = document.getElementById("kpiShortCount");
            if (lCount) lCount.innerText = `${kpis.long_count || 0} Longs`;
            if (sCount) sCount.innerText = `${kpis.short_count || 0} Shorts`;
        }

        function switchChartTab(tab) {
            activeChartTab = tab;
            const tabs = ["dcf", "matrix", "brackets"];
            tabs.forEach(t => {
                const btn = document.getElementById("btnChart" + t.charAt(0).toUpperCase() + t.slice(1));
                if (btn) {
                    if (t === tab) {
                        btn.className = "px-2.5 py-1.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold flex items-center gap-1.5 transition-all text-xs shrink-0 shadow-sm";
                    } else {
                        btn.className = "px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white border border-transparent font-medium flex items-center gap-1.5 transition-all text-xs shrink-0";
                    }
                }
            });
            renderActiveChart();
        }

        function renderActiveChart() {
            const chartData = currentCharts[activeChartTab];
            if (!chartData) return;

            chartData.layout = chartData.layout || {};
            chartData.layout.autosize = true;
            chartData.layout.paper_bgcolor = "#060911";
            chartData.layout.plot_bgcolor = "#0a101f";
            chartData.layout.margin = chartData.layout.margin || { l: 45, r: 25, t: 45, b: 35 };

            Plotly.react("advisorPlotlyBox", chartData.data, chartData.layout, {
                responsive: true,
                displayModeBar: true,
                displaylogo: false
            });
            setTimeout(() => { Plotly.Plots.resize("advisorPlotlyBox"); }, 100);
        }

        function filterTable(type) {
            currentFilter = type;
            const btnAll = document.getElementById("filterBtnAll");
            const btnLong = document.getElementById("filterBtnLong");
            const btnShort = document.getElementById("filterBtnShort");

            btnAll.className = type === 'ALL' ? "px-2.5 py-1 rounded-lg bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 text-xs transition-all" : "px-2.5 py-1 rounded-lg text-slate-400 hover:text-white font-medium text-xs transition-all";
            btnLong.className = type === 'LONG' ? "px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 text-xs transition-all flex items-center gap-1" : "px-2.5 py-1 rounded-lg text-slate-400 hover:text-emerald-400 font-medium text-xs transition-all flex items-center gap-1";
            btnShort.className = type === 'SHORT' ? "px-2.5 py-1 rounded-lg bg-rose-500/20 text-rose-300 font-bold border border-rose-500/40 text-xs transition-all flex items-center gap-1" : "px-2.5 py-1 rounded-lg text-slate-400 hover:text-rose-400 font-medium text-xs transition-all flex items-center gap-1";

            applyFiltersAndRender();
        }

        function onSearchInput(query) {
            applyFiltersAndRender();
        }

        function applyFiltersAndRender() {
            const query = (document.getElementById("tableSearchInput")?.value || "").toLowerCase().trim();
            let filtered = rawRankings;

            if (currentFilter !== "ALL") {
                filtered = filtered.filter(r => r.action_type === currentFilter);
            }

            if (query) {
                filtered = filtered.filter(r => r.symbol.toLowerCase().includes(query) || r.ticker.toLowerCase().includes(query));
            }

            renderTableRows(filtered);
        }

        function renderTableRows(stocks) {
            const tbody = document.getElementById("advisorTableBody");
            if (!tbody) return;

            if (stocks.length === 0) {
                tbody.innerHTML = `<tr><td colspan="12" class="p-8 text-center text-slate-500">No equities match the selected filter criteria.</td></tr>`;
                return;
            }

            let html = "";
            stocks.forEach((r, idx) => {
                const bg = idx % 2 === 0 ? "bg-darkCard/90" : "bg-darkBg/80";
                
                // Action badge styling
                let actionBadge = "";
                if (r.action_type === "LONG") {
                    actionBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>${r.action}</span>`;
                } else if (r.action_type === "SHORT") {
                    actionBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-rose-400"></span>${r.action}</span>`;
                } else {
                    actionBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1 w-fit">${r.action}</span>`;
                }

                // MoS color
                const mosColor = r.margin_of_safety_pct > 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold";
                const mosPrefix = r.margin_of_safety_pct > 0 ? "+" : "";

                html += `
                    <tr class="${bg} hover:bg-slate-800/60 transition-colors">
                        <td class="p-3 whitespace-nowrap font-mono text-slate-400">#${r.rank}</td>
                        <td class="p-3 whitespace-nowrap">
                            <div class="flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full ${r.action_type === 'LONG' ? 'bg-emerald-400' : (r.action_type === 'SHORT' ? 'bg-rose-400' : 'bg-cyan-400')}"></span>
                                <span class="font-bold text-white font-mono text-xs">${r.symbol}</span>
                            </div>
                        </td>
                        <td class="p-3 whitespace-nowrap font-mono text-white font-bold">₹${r.cmp}</td>
                        <td class="p-3 whitespace-nowrap">${actionBadge}</td>
                        <td class="p-3 whitespace-nowrap font-mono font-bold text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20 text-center w-fit">${r.composite_score}</td>
                        <td class="p-3 whitespace-nowrap font-mono text-slate-300">₹${r.dcf_intrinsic_value}</td>
                        <td class="p-3 whitespace-nowrap font-mono ${mosColor}">${mosPrefix}${r.margin_of_safety_pct}%</td>
                        <td class="p-3 whitespace-nowrap font-mono text-slate-300">${r.pe_ratio}</td>
                        <td class="p-3 whitespace-nowrap font-mono text-slate-300">${r.rsi_14}</td>
                        <td class="p-3 whitespace-nowrap font-mono text-emerald-400">₹${r.s1_support}</td>
                        <td class="p-3 whitespace-nowrap font-mono text-cyan-300">₹${r.r1_resistance}</td>
                        <td class="p-3 whitespace-nowrap font-mono text-amber-300 font-semibold">${r.risk_reward}x</td>
                    </tr>
                `;
            });

            tbody.innerHTML = html;
        }

        function refreshData() {
            loadSectorData(currentSector, isGannEnabled);
        }

        function exportToCsv() {
            window.location.href = `/api/export?sector=${encodeURIComponent(currentSector)}&include_gann=${isGannEnabled}`;
        }

        window.addEventListener("resize", () => {
            if (document.getElementById("advisorPlotlyBox")) {
                Plotly.Plots.resize("advisorPlotlyBox");
            }
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8085))
    uvicorn.run(app, host="0.0.0.0", port=port)
