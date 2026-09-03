# 🌌 ALTAIR Quantitative Ecosystem Architecture

This document defines the architectural separation of concerns across the **ALTAIR Quantitative Ecosystem**.

```
                           ┌─────────────────────────────────────────┐
                           │            END-USER CLIENTS             │
                           │     (Retail & Institutional Users)      │
                           └────────────────────┬────────────────────┘
                                                │
                                                ▼
                   ┌────────────────────────────────────────────────────────┐
                   │                     ALTAIR ORION                       │
                   │           Frontend Research & Advisory UI              │
                   │      (advisor.altair-engine.com | Port: 8085)          │
                   │  - Glassmorphic Phone & Desktop Terminal               │
                   │  - Sector DCF Valuation & Fair Values                  │
                   │  - Bi-Directional Alpha Radar (Long vs Short)          │
                   │  - W.D. Gann Square of 9 Harmonics Display             │
                   │  - Model Watchlist Basket Builder                      │
                   └────────────────────────────┬───────────────────────────┘
                                                │
                                    REST API    │  Verified Institutional
                                    Invocations │  Signals & Rankings
                                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         ALTAIR ENGINE                                          │
│                          Core Quantitative Logic & Algorithmic Backend                         │
│                  (api.altair-engine.com | Cloud Run asia-south1 Microservice)                  │
│                                                                                                │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────────────────┐  │
│  │   Intrinsic DCF Model   │  │   Camarilla Channels    │  │   Gann Square of 9 Harmonics   │  │
│  │ - 5-Yr Normalized FCF   │  │ - Dynamic S1 Floor      │  │ - Mathematical Square Roots    │  │
│  │ - 10.5% India WACC Hurdle│  │ - Dynamic R1 Ceiling    │  │ - Cardinal Angles (90°, 180°)  │  │
│  │ - Margin of Safety %    │  │ - Risk/Reward Validation│  │ - Vibration Cycle Scoring      │  │
│  └─────────────────────────┘  └─────────────────────────┘  └────────────────────────────────┘  │
│                                                                                                │
│                 Database & Ingestion Layer: Supabase Cloud PostgreSQL + NSE Feed               │
└───────────────────────────────────────────────▲────────────────────────────────────────────────┘
                                                │
                                    Promoted    │  Strategy API Tests
                                    Formulas    │  & Iteration Signals
                                                │
                   ┌────────────────────────────┴───────────────────────────┐
                   │                    ALTAIR QUANT LAB                    │
                   │            Semi-Backend Strategy R&D Lab               │
                   │        (lab.altair-engine.com | Port: 8080)            │
                   │  - Interactive AI REPL & Prompt Workbench              │
                   │  - Testing Hybrid Formula Combinations                 │
                   │  - Piotroski F-Score + Volatility Regimes              │
                   │  - Mobile Drawer Navigation + Desktop Lab              │
                   │  - Staging Environment Before Engine Promotion         │
                   └────────────────────────────────────────────────────────┘
                                                ▲
                                                │
                           ┌────────────────────┴────────────────────┐
                           │            QUANT RESEARCHERS            │
                           │   (Portfolio Managers, Strategy Devs)   │
                           └─────────────────────────────────────────┘
```

---

## 🏛️ Layer 1: ALTAIR ORION (Client Frontend & Advisory Interface)

* **Directory**: [`advisor/`](file:///d:/ANTI-GRAVITY/ALTAIR%20BASE/advisor/)
* **Production Domain**: `advisor.altair-engine.com`
* **Local Daemon**: Port `8085` (`python -m uvicorn advisor.app:app --port 8085 --reload`)
* **Primary Audience**: End users, retail & HNI investors, institutional analysts.

### Core Responsibilities:
1. **Zero-Friction Visualization**:
   * Presents pre-computed quantitative research cleanly without requiring the user to configure code, mathematical weights, or raw database connection strings.
2. **Glassmorphic Touch-First Design**:
   * **Phone-Optimized**: Native bottom navigation dock, touch-friendly stock cards, 2x2 metric grids, `overscroll-behavior: none`.
   * **Desktop-Ready**: Floating center dock (Linear / Raycast aesthetic) and high-density 13-column financial scorecards.
3. **Institutional Modules**:
   * **📊 Sector DCF**: Intrinsic valuations across 10 core NSE sector universes (Top 20 each).
   * **🎯 Bi-Directional Alpha Radar**: Parallel breakdown of top accumulation longs vs overvalued short hedge candidates.
   * **🔮 W.D. Gann Hub**: Geometric vibration pivots and harmonic turning degrees ($45^\circ, 90^\circ, 135^\circ, 180^\circ$).
   * **💼 Model Watchlist**: Custom portfolio basket aggregator computing weighted margin of safety and P/E ratios.

---

## 🧪 Layer 2: ALTAIR QUANT LAB (Semi-Backend Strategy R&D Lab)

* **Directory**: [`quant_lab/`](file:///d:/ANTI-GRAVITY/ALTAIR%20BASE/quant_lab/)
* **Production Domain**: `lab.altair-engine.com`
* **Local Daemon**: Port `8080` (`python -m uvicorn app:app --port 8080 --reload`)
* **Primary Audience**: Quant engineers, algorithmic developers, strategy researchers.

### Core Responsibilities:
1. **Strategy Sandbox & Iteration Workbench**:
   * The "semi-backend" experimentation ground where new algorithmic formulas are tested and refined.
   * Allows rapid testing of hybrid combinations (e.g. *DCF Fair Value + Gann 90-degree Confluence + 14-Day RSI Oversold + Institutional Delivery Spike*).
2. **Interactive Workbench**:
   * Natural-language query interface with live python execution, session management, and persistent chat trajectories.
   * Direct database queries to inspect raw valuation metrics and backtest historical performance.
3. **Staging & Promotion Gate**:
   * No untested formula goes straight to end users in ORION.
   * Once a quantitative model achieves statistical significance and risk/reward robustness in Quant Lab, its logic is distilled into **ALTAIR ENGINE**.

---

## ⚙️ Layer 3: ALTAIR ENGINE (Algorithmic Core Backend & Data Pipelines)

* **Directory**: [`backend/`](file:///d:/ANTI-GRAVITY/ALTAIR%20BASE/backend/) / [`advisor/engine.py`](file:///d:/ANTI-GRAVITY/ALTAIR%20BASE/advisor/engine.py)
* **Production Domain**: `api.altair-engine.com` / Cloud Run Asia-South1
* **Primary Audience**: Headless microservices, cron workers, frontend API consumers.

### Core Responsibilities:
1. **Mathematical Financial Valuation**:
   * **Normalized DCF**: 5-year free cash flow projections, India-specific 10.5% WACC cost of capital hurdle, terminal growth compounding.
   * **Margin of Safety**: Percentage delta between CMP and calculated fair intrinsic value:
     $$\text{Margin of Safety} = \frac{\text{DCF Intrinsic Value} - \text{CMP}}{\text{CMP}} \times 100\%$$
2. **Technical & Geometric Harmonics**:
   * **Camarilla S1 / R1 Brackets**: Algorithmic calculation of floor support stop-loss levels and ceiling targets with ATR validation.
   * **W.D. Gann Square of 9**: Square root matrix calculations predicting mathematical price vibration angles.
3. **Data Pipelines & Ingestion**:
   * Real-time and historical price ingestion via NSE feeds and Yahoo Finance.
   * Enterprise persistence on **Supabase Cloud PostgreSQL** (`aws-0-ap-south-1`).
   * Clean JSON REST API interfaces consumed by both **ALTAIR ORION** and **ALTAIR QUANT LAB**.

---

## 🔄 Separation of Concerns Workflow

```
[ New Hypothesis / Idea ]
           │
           ▼
[ 1. QUANT LAB R&D ]  <-- Experiment with parameters, formulas, and weights
           │
           ▼
[ 2. ALTAIR ENGINE ]  <-- Hard-code validated logic into high-performance backend pipelines
           │
           ▼
[ 3. ALTAIR ORION ]   <-- Render verified signals into clean, consumer-ready glassmorphic UI
```

This clean architecture ensures:
* **Stability**: End users on ORION never experience broken sandbox scripts or half-baked formulas.
* **Agility**: Quant researchers have unrestricted freedom in Quant Lab to tweak code without risking client downtime.
* **Scalability**: ALTAIR ENGINE scales independently as a headless cloud service.
