import os
import requests
import logging

logger = logging.getLogger("UpstoxClient")

# Base API URL
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

# Token loaded from .env
UPSTOX_ACCESS_TOKEN = os.environ.get("UPSTOX_ACCESS_TOKEN")

# Ticker to ISIN mapping for the supported universe of Indian stocks
TICKER_INFO_MAP = {
    "RELIANCE.NS": {"isin": "INE002A01018", "symbol": "RELIANCE", "shares": 6760000000.0},
    "TCS.NS": {"isin": "INE467B01029", "symbol": "TCS", "shares": 3620000000.0},
    "INFY.NS": {"isin": "INE009A01021", "symbol": "INFY", "shares": 4150000000.0},
    "HDFCBANK.NS": {"isin": "INE040A01034", "symbol": "HDFCBANK", "shares": 7600000000.0},
    "ICICIBANK.NS": {"isin": "INE090A01021", "symbol": "ICICIBANK", "shares": 7000000000.0},
    "SBIN.NS": {"isin": "INE062A01020", "symbol": "SBIN", "shares": 8920000000.0},
    "ZOMATO.NS": {"isin": "INE758T01015", "symbol": "ZOMATO", "shares": 8800000000.0},
    "PAYTM.NS": {"isin": "INE982J01020", "symbol": "PAYTM", "shares": 635000000.0},
    "NYKAA.NS": {"isin": "INE0DD101010", "symbol": "NYKAA", "shares": 2850000000.0},
    "DELHIVERY.NS": {"isin": "INE148O01028", "symbol": "DELHIVERY", "shares": 735000000.0},
    "HONASA.NS": {"isin": "INE0J5401028", "symbol": "HONASA", "shares": 323000000.0},
    "CARTRADE.NS": {"isin": "INE290U01011", "symbol": "CARTRADE", "shares": 47000000.0},
    "POLICYBZR.NS": {"isin": "INE417T01026", "symbol": "POLICYBZR", "shares": 450000000.0},
}

def call_upstox_api(endpoint: str, params: dict = None) -> dict:
    """Executes a GET request to the Upstox API v2 with auth headers."""
    if not UPSTOX_ACCESS_TOKEN:
        raise ValueError("UPSTOX_ACCESS_TOKEN is not set in environment variables.")
        
    url = f"{UPSTOX_BASE_URL}{endpoint}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {UPSTOX_ACCESS_TOKEN}"
    }
    
    r = requests.get(url, headers=headers, params=params, timeout=15)
    if r.status_code != 200:
        logger.error(f"Upstox API returned error {r.status_code}: {r.text}")
        raise ValueError(f"Upstox API Error: {r.status_code}")
        
    data = r.json()
    if data.get("status") != "success":
        logger.error(f"Upstox API failed: {data}")
        raise ValueError(f"Upstox API failure response: {data.get('errors')}")
        
    return data

def fetch_upstox_financials(ticker: str) -> dict:
    """Retrieves financials and price data from Upstox API and compiles standard intrinsic input metrics."""
    if ticker not in TICKER_INFO_MAP:
        raise ValueError(f"Ticker {ticker} is not mapped in Upstox universe.")
        
    info = TICKER_INFO_MAP[ticker]
    isin = info["isin"]
    shares = info["shares"]
    
    # 1. Fetch Quote (LTP)
    quote_res = call_upstox_api(f"/market-quote/ltp?instrument_key=NSE_EQ%7C{isin}")
    cmp = None
    for k, v in quote_res.get("data", {}).items():
        cmp = v.get("last_price")
    if not cmp:
        raise ValueError(f"Could not retrieve last price for {ticker} from Upstox")
        
    # 2. Fetch Balance Sheet
    bs_res = call_upstox_api(f"/fundamentals/{isin}/balance-sheet")
    bs_history = bs_res.get("data", {}).get("history", [])
    total_assets = 0.0
    total_liabilities = 0.0
    if bs_history:
        # Upstox returns numbers in Crores, scale to absolute INR (multiply by 10^7)
        total_assets = bs_history[0].get("total_asset", 0) * 10000000.0
        total_liabilities = bs_history[0].get("total_liability", 0) * 10000000.0
        
    # 3. Fetch Income Statement
    inc_res = call_upstox_api(f"/fundamentals/{isin}/income-statement")
    net_profit = 0.0
    ebit = 0.0
    revenue = 0.0
    for item in inc_res.get("data", {}).get("income_statement", []):
        cat = item.get("category", "").lower()
        history = item.get("history", [])
        if not history:
            continue
        val = history[0].get("value", 0) * 10000000.0
        if "net_profit" in cat or "net_income" in cat:
            net_profit = val
        elif "ebit" in cat or "operating_profit" in cat:
            ebit = val
        elif "revenue" in cat or "turnover" in cat:
            revenue = val
            
    # 4. Fetch Cash Flow
    cf_res = call_upstox_api(f"/fundamentals/{isin}/cash-flow")
    op_cash_flow = 0.0
    capex = 0.0
    for item in cf_res.get("data", {}).get("cash_flow", []):
        cat = item.get("category", "").lower()
        history = item.get("history", [])
        if not history:
            continue
        val = history[0].get("value", 0) * 10000000.0
        if "operating" in cat:
            op_cash_flow = val
        elif "investing" in cat:
            capex = abs(val) if val < 0 else val * 0.5
            
    # Computations
    fcf_0 = op_cash_flow - capex
    if fcf_0 <= 0:
        fcf_0 = op_cash_flow or (total_assets * 0.05) # fallback to 5% of assets
        
    eps = net_profit / shares if shares > 0 else 1.0
    if eps <= 0:
        eps = 1.0
        
    # Cash equivalents proxy
    cash_equivalents = total_assets * 0.08
    
    # Calculate WACC and metrics (Indian parameters)
    rf_rate = 0.07
    bond_yield = 7.0
    market_premium = 0.065
    tax_rate = 0.25
    beta = 1.1
    
    cost_of_equity = rf_rate + (beta * market_premium)
    cost_of_debt = 0.08
    
    equity_val = cmp * shares
    total_val = equity_val + total_liabilities
    
    w_equity = equity_val / total_val if total_val > 0 else 1.0
    w_debt = total_liabilities / total_val if total_val > 0 else 0.0
    
    wacc = (w_equity * cost_of_equity) + (w_debt * cost_of_debt * (1 - tax_rate))
    wacc = max(0.08, wacc) # floor at 8%
    
    # Growth rate estimate (e.g. 12% average)
    growth_rate = 0.12
    
    return {
        "ticker": ticker,
        "cmp": float(cmp),
        "fcf_0": float(fcf_0),
        "shares_outstanding": float(shares),
        "total_debt": float(total_liabilities),
        "cash_equivalents": float(cash_equivalents),
        "eps": float(eps),
        "dividend_per_share": float(0.0),
        "growth_rate": float(growth_rate),
        "wacc": float(wacc),
        "cost_of_equity": float(cost_of_equity),
        "bond_yield": float(bond_yield),
        "source": "Upstox Analytics API"
    }
