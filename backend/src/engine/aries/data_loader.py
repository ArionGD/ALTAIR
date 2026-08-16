import yfinance as yf
import logging

logger = logging.getLogger("AriesDataLoader")

def load_financial_data(ticker_symbol: str) -> dict:
    """Fetches real-time and historical financial metrics using yfinance 
    and computes input parameters (including WACC) for intrinsic value models.
    """
    logger.info(f"Loading financial metrics from yfinance for {ticker_symbol}...")
    
    # 1. Initialize ticker
    t = yf.Ticker(ticker_symbol)
    info = t.info or {}
    
    # Check if Indian stock
    is_indian = ticker_symbol.upper().endswith(".NS") or ticker_symbol.upper().endswith(".BO")
    
    # Setup sovereign default rates
    rf_rate = 0.07 if is_indian else 0.04          # Risk-Free Rate
    bond_yield = 7.0 if is_indian else 4.0        # Y for Benjamin Graham formula
    market_premium = 0.065 if is_indian else 0.055 # Market Risk Premium (Rm - Rf)
    tax_rate = 0.25                              # Average corporate tax rate
    
    # 2. Basic Stock Price & Shares
    cmp = info.get("currentPrice") or info.get("regularMarketPrice")
    if not cmp:
        # Fallback to history Close
        try:
            hist = t.history(period="5d")
            if not hist.empty:
                cmp = float(hist["Close"].iloc[-1])
        except Exception:
            pass
    if not cmp:
        cmp = 100.0  # Safe default to avoid crashes
        
    shares = info.get("sharesOutstanding")
    if not shares:
        # Check balance sheet
        try:
            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                # Common shares outstanding is often a row
                for idx in bs.index:
                    if "shares" in idx.lower() or "common stock" in idx.lower():
                        shares = float(bs.loc[idx].iloc[0])
                        break
        except Exception:
            pass
    if not shares or shares <= 0:
        shares = 1.0  # Prevent division by zero
        
    # 3. Income Statement / Cash Flow variables
    eps = info.get("trailingEps") or info.get("forwardEps") or 1.0
    div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0
    
    # 4. FCF (Free Cash Flow to Firm/Equity)
    # Default formula: Operating Cash Flow - CapEx
    op_cash_flow = 0.0
    capex = 0.0
    interest_expense = 0.0
    ebit = 0.0
    
    try:
        cf = t.cashflow
        if cf is not None and not cf.empty:
            # Match Operating Cash Flow
            for idx in cf.index:
                if "operating" in idx.lower() and "cash" in idx.lower():
                    op_cash_flow = float(cf.loc[idx].iloc[0])
                if "capital" in idx.lower() and "expenditure" in idx.lower():
                    capex = abs(float(cf.loc[idx].iloc[0])) # ensure positive value
    except Exception as e:
        logger.warning(f"Error fetching Cash Flow statements for {ticker_symbol}: {e}")
        
    try:
        income = t.financials
        if income is not None and not income.empty:
            for idx in income.index:
                if "interest" in idx.lower() and "expense" in idx.lower():
                    interest_expense = abs(float(income.loc[idx].iloc[0]))
                if "ebit" in idx.lower() or "operating income" in idx.lower():
                    ebit = float(income.loc[idx].iloc[0])
    except Exception as e:
        logger.warning(f"Error fetching Income statements for {ticker_symbol}: {e}")

    fcf_0 = op_cash_flow - capex
    # Fallback to info-based FCF if statement FCF is negative/empty
    if fcf_0 <= 0:
        fcf_0 = info.get("freeCashflow") or op_cash_flow or (cmp * shares * 0.05) # fallback to 5% of market cap
        
    # 5. Balance Sheet variables
    total_debt = info.get("totalDebt") or 0.0
    total_cash = info.get("totalCash") or 0.0
    
    try:
        bs = t.balance_sheet
        if bs is not None and not bs.empty:
            cash_vals = []
            debt_vals = []
            for idx in bs.index:
                if "cash and cash equivalents" in idx.lower() or "cash cash equivalents" in idx.lower():
                    cash_vals.append(float(bs.loc[idx].iloc[0]))
                if "long term debt" in idx.lower() or "short term debt" in idx.lower() or "total debt" in idx.lower():
                    debt_vals.append(float(bs.loc[idx].iloc[0]))
            if cash_vals:
                total_cash = max(cash_vals)
            if debt_vals:
                total_debt = sum(debt_vals)
    except Exception as e:
        logger.warning(f"Error fetching Balance Sheet for {ticker_symbol}: {e}")
        
    # 6. WACC Components
    beta = info.get("beta")
    if not beta or beta <= 0:
        beta = 1.1 if is_indian else 1.0 # beta defaults
        
    # Cost of Equity (CAPM)
    cost_of_equity = rf_rate + (beta * market_premium)
    
    # Cost of Debt (Interest Expense / Total Debt)
    cost_of_debt = 0.06 # default 6%
    if total_debt > 0 and interest_expense > 0:
        cost_of_debt = interest_expense / total_debt
        if cost_of_debt > 0.20: # Cap at 20% to avoid outliers
            cost_of_debt = 0.08
            
    # WACC Weights
    equity_val = cmp * shares
    total_val = equity_val + total_debt
    
    w_equity = equity_val / total_val if total_val > 0 else 1.0
    w_debt = total_debt / total_val if total_val > 0 else 0.0
    
    wacc = (w_equity * cost_of_equity) + (w_debt * cost_of_debt * (1 - tax_rate))
    
    # Minimum WACC floor of 6% to ensure conservative discounting
    wacc = max(0.06, wacc)
    
    # 7. Growth Rate Estimations
    # Sector based defaults or info-based revenue/earnings growth
    growth_rate = info.get("earningsGrowth") or info.get("revenueGrowth") or 0.10
    # Restrict growth rate within conservative bounds (5% to 25%)
    growth_rate = max(0.05, min(0.25, growth_rate))
    
    return {
        "ticker": ticker_symbol,
        "cmp": float(cmp),
        "fcf_0": float(fcf_0),
        "shares_outstanding": float(shares),
        "total_debt": float(total_debt),
        "cash_equivalents": float(total_cash),
        "eps": float(eps),
        "dividend_per_share": float(div_rate),
        "growth_rate": float(growth_rate),
        "wacc": float(wacc),
        "cost_of_equity": float(cost_of_equity),
        "bond_yield": float(bond_yield)
    }
