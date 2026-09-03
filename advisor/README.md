# 🌟 ALTAIR ORION (`advisor/`)

**Production Subdomain**: `advisor.altair-engine.com`  
**Local Port**: `8085` (`python -m uvicorn advisor.app:app --port 8085 --reload`)

## Purpose & Scope
ALTAIR ORION is the **User-Facing Production Client / Interface** for normal users and institutional investors. It consumes evaluated quantitative signals, DCF valuations, and Camarilla price channels from **ALTAIR ENGINE** and presents them in a clean, high-performance, glassmorphic UI.

## Key Features
* **Glassmorphic Touch UI**:
  * Blue and white luminous ambient glowing spots.
  * Mobile phone view: Native bottom dock, touch stock cards, `overscroll-behavior: none`.
  * Desktop view: Centered floating dock, 13-column financial scorecard.
* **4 Core Modules**:
  1. `📊 Sector DCF`: Top 20 stocks ranked across 10 core NSE sectors with DCF Fair Value and Margin of Safety.
  2. `🎯 Alpha Radar`: Bi-directional accumulation longs vs overvalued short candidates.
  3. `🔮 Gann Hub`: W.D. Gann Square of 9 Harmonics ($45^\circ, 90^\circ, 135^\circ, 180^\circ$).
  4. `💼 Watchlist`: Model basket builder with weighted portfolio valuation metrics.
* **Clean Architecture**:
  * `templates/orion.html`: Dedicated modular template.
  * Dynamic logo resolver (`orion_logo.png` fallback).

For complete ecosystem details, see [ARCHITECTURE.md](../ARCHITECTURE.md).
