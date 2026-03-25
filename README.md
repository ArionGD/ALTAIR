# 🏛️ ALTAIR Base: Financial Predation Engine (Backend-AI)

ALTAIR is a high-precision backend-AI designed to identify "systemically weak" companies (**Glass Pillars**) for short-selling strategies, specifically optimized for the predicted market fracture on **April 19, 2026**.

---

## 🏛️ Core Architecture: The Triple-Tier Predation Engine
1.  **ORION (The Mind)**: Macro-Astro timing engine (April 2026 Reset focus).
2.  **ALTAIR (The Blade)**: Financial vulnerability ranking engine (Micro-Forensics).
3.  **PHOENIX (The Body)**: FastAPI-powered backend serving strike data to the frontend.

---

## 🏹 AVS V4.0 Forensic Metrics (The "Margin Call" Tier)
ALTAIR utilizes a 5-dimensional scoring system to identify the weakest links:
- **30% Fundamental Bubble**: PE-Ratio (>150) and Debt-to-Equity (>200) density.
- **25% Z-Score (Solvency)**: Altman Z-Score < 1.8 indicates high bankruptcy risk.
- **20% Pledge Rate (PR)**: Founder margin-call vulnerability (Hidden Debt).
- **15% Sentiment Decay**: Real-time news Scavenging for "Fear" keywords.
- **10% VIX Beta (Panic)**: Sensitivity to market volatility spikes.

---

## 🛠️ API Integration Guide (For PHOENIX Dashboard)

The ALTAIR backend runs on **Port 8001**. All endpoints are versioned under `/api/v1`.

### 1. **Health Check** (Dashboard Heartbeat)
Verify the engine state and data readiness.
- **Endpoint**: `GET http://127.0.0.1:8001/api/v1/health`
- **PowerShell**: `Invoke-RestMethod -Uri "http://127.0.0.1:8001/api/v1/health"`

### 2. **Full Strike List** (The Strike Map)
Returns the high-detail V4.0 forensic metrics for all audited tickers.
- **Endpoint**: `GET http://127.0.0.1:8001/api/v1/forensic-metrics`
- **Frontend Filter Example (JS):**
  ```javascript
  const indConsumerTech = data.filter(item => 
      item.ticker.endsWith('.NS') && 
      item.sector === 'Consumer_Tech_Beauty'
  );
  ```

### 3. **Ticker Detail** (Deep Forensic Breakdown)
Get the exact scores for a specific stock (e.g., Nykaa).
- **Endpoint**: `GET http://127.0.0.1:8001/api/v1/forensic-ticker/NYKAA.NS`

### 4. **Live Research** (Trigger Forensic Audit)
Initiate a fresh bilateral (US/IND) data collection and audit in the background.
- **Endpoint**: `POST http://127.0.0.1:8001/api/v1/audit`

---

## 🚀 Getting Started
1. **Install Dependencies**: `pip install -r requirements.txt`
2. **Start the Engine**: `python main.py`
3. **Interactive Documentation**: `http://127.0.0.1:8001/docs`

**Strategic Verdict**: DO NOT focus on the daily price (The Illusion). Focus on the **AVS V4.0 Score** (The Truth).
