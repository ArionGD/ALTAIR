# 🏛️ ALTAIR: Operation Aladdin (Scenario Engine Blueprint)

## 1. Concept: The "What-If" Sovereign Orchestrator
The goal of Operation Aladdin is to transition ALTAIR from a static auditor into a **Reactive Simulation Engine.** We will calculate the probability of a "Fracture" based on real-world geopolitical and macro-economic events.

---

## 2. The Sensitivity Matrix (The "Beta" Map)
Every company in the ALTAIR portfolio must be mapped to four **"Sensitivity Coefficients"** (0.0 to 2.0):

| Variable | **Symbol** | **Description** |
| :--- | :--- | :--- |
| **Energy Beta** | `β_oil` | Sensitivity to Crude Oil spikes (Logistics/Industrial). |
| **Supply-Chain Beta** | `β_semi` | Dependency on TSMC/Hardware/China-Taiwan lanes. |
| **Capital Beta** | `β_fii` | Sensitivity to Foreign Institutional Outflow. |
| **Volatility Beta** | `β_vix` | General 'Flight-to-Safety' during global war scenarios. |

---

## 3. The Scenario Logic (The Calculation Engine)

To calculate the **Projected Strike Price ($P_{strike}$)** during a scenario, we use the following weighted formula:

$$P_{strike} = P_{current} \times (1 - \Sigma(\Delta_{scenario} \times \beta_{ticker}) \times W_{forensic})$$

### **Scenario Cases:**
1.  **The "Middle East Fracture" (Oil Focus)**
    - Trigger: Brent Crude > $110
    - Multiplier: High on `β_oil` (Delhivery, Uber, AMZN).
2.  **The "Taiwan Strait Freeze" (Semi Focus)**
    - Trigger: TSMC Shipment Blockade.
    - Multiplier: High on `β_semi` (AAPL, NVDA, AMD, MSFT).
3.  **The "Sovereign Default" (FII/FDI Focus)**
    - Trigger: US Fed Rates > 6% or Geopolitical Conflict.
    - Multiplier: High on `β_fii` (All Indian Consumer Tech & US Bubble Tech).

---

## 4. Building the Engine (Development Roadmap)

### **Phase 1: Knowledge Mapping**
- Create `src/engine/aladdin/SensitivityMatrix.py`.
- Map the Top 40 tickers (US + India) to their respective Betas.

### **Phase 2: The Simulator**
- Create `src/engine/aladdin/ScenarioOrchestrator.py`.
- This script will take inputs: `run_sim(scenario='taiwan_blockade', intensity=0.8)`.

### **Phase 3: Dynamic Ranking**
- Output a new CSV: `ALADDIN_STRIKE_PRIORITY.csv`.
- Rank stocks not by their current price, but by their **"Fracture Potential"** in the selected scenario.

---

## 5. Summary: Target "Supernova" Logic
Operation Aladdin targets the **"Asymmetric Return."** If a stock has a **Negative Sloan Ratio** (Forensic weakness) and is highly sensitive to a **TSMC Blockade** (Macro weakness), that stock is a **Level 1 Priority Strike Target.**

**The engine is now in the Ideation/Architecture phase. Use this blueprint to guide the V12.0 Aladdin build.** 🏹🏛️⚖️
