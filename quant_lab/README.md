# 🧪 ALTAIR QUANT LAB (`quant_lab/`)

**Production Subdomain**: `lab.altair-engine.com`  
**Local Port**: `8080` (`python -m uvicorn app:app --port 8080 --reload`)

## Purpose & Scope
ALTAIR QUANT LAB is the **Semi-Backend Strategy R&D Lab & Iteration Workbench**. It is the dedicated engineering environment for quant developers and researchers to experiment with, test, and iterate on different mathematical formulas, alpha signals, and data combinations before promoting them to **ALTAIR ENGINE**.

## Key Features
* **Interactive Quantitative Workbench**:
  * AI-assisted REPL & execution environment.
  * Direct access to market data, Supabase PostgreSQL, and mathematical libraries.
  * Rapid parameter tuning (e.g. testing different WACC discount rates, Gann vibration steps, and RSI bounds).
* **Cross-Device Usability**:
  * Desktop terminal workbench layout.
  * Mobile phone view with collapsible 3-dash hamburger drawer overlay.
* **Separation of Concerns**:
  * Serves as the experimental sandbox.
  * Validated models are distilled into `advisor/engine.py` / `backend/` for production consumption by **ALTAIR ORION**.

For complete ecosystem details, see [ARCHITECTURE.md](../ARCHITECTURE.md).
