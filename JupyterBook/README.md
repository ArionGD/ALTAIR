# 🚀 ALTAIR STE Quantitative Research Lab (`JupyterBook`)

This directory contains the official quantitative research and algorithmic fine-tuning environment for the **ALTAIR Swing Trade Engine (STE)**.

---

## 📂 Contents
*   **`ste_engine_lab.ipynb`**: The primary research notebook featuring:
    1.  **Data Ingestion**: Multi-ticker daily OHLCV bars (yfinance).
    2.  **Indicator Calculations**: 50/200 DMA, Wilder RSI(14), Up/Down Volume Ratio proxy, 14-day ATR.
    3.  **Dual-Gate Strategy Logic**: Fundamental Gate (`astra_strike_score`) + Technical Momentum.
    4.  **Trade Simulator**: Dynamic ATR-based Entry, Target (2:1 RRR), and Stop Loss.
    5.  **Scorecards**: Win Rate %, Profit Factor, Trade Log breakdown.
    6.  **Plotly Candlestick Visualizer**: Candlestick charts with Buy/Sell markers.
    7.  **Parameter Calibration (Grid Search)**: Multi-parameter optimization across core stocks.
    8.  **Gemini AI Quant Copilot**: Direct AI analysis and strategy critiquing inside the notebook.
*   **`launch_lab.bat`**: One-click Windows launcher to start the Jupyter server locally.

---

## ⚡ How to Run Locally

### Method 1: Double-Click
Double-click **`launch_lab.bat`** in this folder. Your default web browser will open at:
```
http://localhost:8888/tree
```

### Method 2: Terminal / PowerShell
From the project root:
```bash
python -m notebook --notebook-dir="JupyterBook" --port=8888
```

---

## 🤖 Activating Gemini Inside the Notebook
To enable the AI Quant Copilot cell in the notebook, make sure your `GEMINI_API_KEY` is present in `backend/.env` or set in your environment:
```python
os.environ["GEMINI_API_KEY"] = "your-api-key-here"
```

---

## ☁️ Moving to GCP (Free Credits)
Once you are satisfied with the local testing experience, this entire `JupyterBook/` setup can be uploaded directly to:
1.  **Google Colab**: [colab.research.google.com](https://colab.research.google.com) (Instant, free cloud execution).
2.  **GCP Vertex AI Workbench**: Cloud-hosted JupyterLab instance running on an `e2-standard-2` VM under your GCP project credits.
