import logging

logger = logging.getLogger("AriesEngine")

def calculate_dcf_intrinsic_value(
    fcf_0: float,           # Current Year Free Cash Flow (FCFE or FCFF)
    shares_outstanding: float,
    total_debt: float,
    cash_equivalents: float,
    growth_rate_5yr: float, # e.g., 0.12 for 12%
    terminal_growth: float, # e.g., 0.035 for 3.5%
    wacc: float,            # e.g., 0.10 for 10%
    projection_years: int = 5
) -> dict:
    """Calculates intrinsic value using the Discounted Cash Flow (DCF) model."""
    try:
        if shares_outstanding <= 0:
            return {"status": "error", "message": "Shares outstanding must be positive"}

        # Prevent division by zero if WACC <= terminal growth
        if wacc <= terminal_growth:
            logger.warning("WACC is less than or equal to terminal growth rate. Setting minimum spread of 3.0%.")
            wacc = terminal_growth + 0.03

        # 1. Project future cash flows and discount to Present Value (PV)
        pv_projected_fcf = 0.0
        future_fcf = fcf_0
        projected_flows = []
        
        for year in range(1, projection_years + 1):
            future_fcf *= (1 + growth_rate_5yr)
            discount_factor = (1 + wacc) ** year
            pv_fcf = future_fcf / discount_factor
            pv_projected_fcf += pv_fcf
            projected_flows.append({
                "year": year,
                "projected_fcf": round(future_fcf, 2),
                "pv_fcf": round(pv_fcf, 2)
            })

        # 2. Terminal Value Calculation
        fcf_terminal = future_fcf * (1 + terminal_growth)
        terminal_value = fcf_terminal / (wacc - terminal_growth)
        pv_terminal_value = terminal_value / ((1 + wacc) ** projection_years)

        # 3. Enterprise Value to Equity Value
        enterprise_value = pv_projected_fcf + pv_terminal_value
        equity_value = enterprise_value - total_debt + cash_equivalents
        
        # 4. Intrinsic Value per share
        intrinsic_value_per_share = equity_value / shares_outstanding
        
        return {
            "status": "success",
            "model": "Discounted Cash Flow (DCF)",
            "projected_flows": projected_flows,
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal_value, 2),
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "intrinsic_value": max(0.0, round(intrinsic_value_per_share, 2))
        }
    except Exception as e:
        logger.error(f"Error in DCF calculation: {e}")
        return {"status": "error", "message": str(e)}

def calculate_graham_intrinsic_value(
    eps: float,             # Trailing 12-Month Earnings Per Share
    growth_rate: float,     # Expected annual growth rate as a whole number (e.g., 10 for 10%)
    bond_yield: float,      # Current 10-Year Government Bond Yield (e.g., 4.0 for US, 7.0 for IND)
    base_pe: float = 8.5,   # P/E base for a no-growth company
    bond_multiplier: float = 4.4 # Historical top-rated corporate bond average yield
) -> dict:
    """Calculates intrinsic value using the Revised Benjamin Graham Formula:
    V* = (EPS * (base_pe + 2g) * bond_multiplier) / Y
    """
    try:
        # Prevent division by zero if bond yield is zero or negative
        if bond_yield <= 0:
            logger.warning("Bond yield must be positive. Falling back to default yield of 4.4%.")
            bond_yield = 4.4

        # Graham's growth rate is a whole number in the formula (e.g., 10 for 10% growth)
        # If passed as a float less than 1, scale it up to a whole number representation
        if 0.0 < growth_rate < 1.0:
            growth_rate *= 100

        intrinsic_value = (eps * (base_pe + 2 * growth_rate) * bond_multiplier) / bond_yield
        
        return {
            "status": "success",
            "model": "Revised Benjamin Graham Formula",
            "eps": round(eps, 2),
            "growth_rate_used": round(growth_rate, 2),
            "bond_yield": round(bond_yield, 2),
            "intrinsic_value": max(0.0, round(intrinsic_value, 2))
        }
    except Exception as e:
        logger.error(f"Error in Graham calculation: {e}")
        return {"status": "error", "message": str(e)}

def calculate_ddm_intrinsic_value(
    d_0: float,             # Trailing Annual Dividend per share
    cost_of_equity: float,  # Required rate of return r (e.g., 0.10 for 10%)
    dividend_growth: float  # Expected constant growth rate g (e.g., 0.05 for 5%)
) -> dict:
    """Calculates intrinsic value using the Gordon Growth Dividend Discount Model (DDM):
    P0 = D1 / (r - g)
    """
    try:
        # Prevent division by zero or negative denominator
        if cost_of_equity <= dividend_growth:
            logger.warning("Cost of equity is less than or equal to dividend growth rate. Adjusting cost of equity.")
            cost_of_equity = dividend_growth + 0.03

        # D1 = expected dividend next year
        d_1 = d_0 * (1 + dividend_growth)
        intrinsic_value = d_1 / (cost_of_equity - dividend_growth)

        return {
            "status": "success",
            "model": "Dividend Discount Model (Gordon Growth)",
            "d0": round(d_0, 2),
            "d1": round(d_1, 2),
            "cost_of_equity": round(cost_of_equity, 4),
            "dividend_growth": round(dividend_growth, 4),
            "intrinsic_value": max(0.0, round(intrinsic_value, 2))
        }
    except Exception as e:
        logger.error(f"Error in DDM calculation: {e}")
        return {"status": "error", "message": str(e)}

def get_margin_of_safety(intrinsic_value: float, cmp: float) -> dict:
    """Applies the Margin of Safety decision matrix against the current market price (CMP)."""
    if intrinsic_value <= 0:
        return {
            "margin_of_safety_pct": 0.0,
            "status": "Overvalued / Premium",
            "action": "Avoid / Trim Exposure"
        }

    margin_of_safety = ((intrinsic_value - cmp) / intrinsic_value) * 100
    
    if margin_of_safety > 25.0:
        status = "Deeply Undervalued"
        action = "Tranche Buy Signal (High priority)"
    elif 0.0 <= margin_of_safety <= 25.0:
        status = "Fairly Valued"
        action = "Hold / Accumulate on Support"
    elif -20.0 <= margin_of_safety < 0.0:
        status = "Fully Priced"
        action = "Neutral / Watchlist"
    else:
        status = "Overvalued / Premium"
        action = "Avoid / Trim Exposure"

    return {
        "margin_of_safety_pct": round(margin_of_safety, 2),
        "status": status,
        "action": action
    }

def evaluate_intrinsic_value(
    ticker: str,
    cmp: float,
    fcf_0: float,
    shares_outstanding: float,
    total_debt: float,
    cash_equivalents: float,
    eps: float,
    dividend_per_share: float,
    growth_rate: float,        # expected growth as decimal (e.g. 0.10)
    wacc: float,               # WACC as decimal (e.g. 0.10)
    cost_of_equity: float,     # cost of equity as decimal (e.g. 0.11)
    bond_yield: float          # 10Y Bond yield as percentage (e.g. 4.0)
) -> dict:
    """Executes and compiles all three intrinsic valuation models, selecting the 
    most applicable model based on the target stock's profiles.
    """
    # 1. Run all three calculations
    dcf_res = calculate_dcf_intrinsic_value(
        fcf_0=fcf_0,
        shares_outstanding=shares_outstanding,
        total_debt=total_debt,
        cash_equivalents=cash_equivalents,
        growth_rate_5yr=growth_rate,
        terminal_growth=0.03, # standard terminal growth matching GDP ~3%
        wacc=wacc
    )
    
    graham_res = calculate_graham_intrinsic_value(
        eps=eps,
        growth_rate=growth_rate, # will scale up inside graham calc if decimal
        bond_yield=bond_yield
    )
    
    ddm_res = calculate_ddm_intrinsic_value(
        d_0=dividend_per_share,
        cost_of_equity=cost_of_equity,
        dividend_growth=min(growth_rate, 0.06) # cap long-term dividend growth at 6% for conservatism
    )

    # 2. Determine best model mapping
    # - If dividend yield is high (Dividend DPS / CMP > 4.5%), choose Gordon DDM
    # - Else if FCF is positive, choose DCF
    # - Else fallback to Graham Formula as baseline screener
    div_yield = (dividend_per_share / cmp) if cmp > 0 else 0
    
    if div_yield > 0.045 and ddm_res.get("status") == "success" and ddm_res["intrinsic_value"] > 0:
        recommended_model = "Dividend Discount Model (Gordon Growth)"
        recommended_intrinsic_value = ddm_res["intrinsic_value"]
        rationale = "High-dividend profile (yield > 4.5%). Dividend Discount Model provides the most reliable valuation."
    elif fcf_0 > 0 and dcf_res.get("status") == "success" and dcf_res["intrinsic_value"] > 0:
        recommended_model = "Discounted Cash Flow (DCF)"
        recommended_intrinsic_value = dcf_res["intrinsic_value"]
        rationale = "Positive Free Cash Flow company. Discounted Cash Flow model provides the most fundamental valuation."
    else:
        recommended_model = "Revised Benjamin Graham Formula"
        recommended_intrinsic_value = graham_res["intrinsic_value"] if graham_res.get("status") == "success" else 0.0
        rationale = "Valued via Benjamin Graham screening equation due to negative/erratic free cash flows or low dividend yield."

    # 3. Apply Margin of Safety
    mos_analysis = get_margin_of_safety(recommended_intrinsic_value, cmp)

    return {
        "ticker": ticker,
        "current_market_price": cmp,
        "recommended_model": recommended_model,
        "recommended_intrinsic_value": recommended_intrinsic_value,
        "valuation_rationale": rationale,
        "margin_of_safety": mos_analysis,
        "models": {
            "dcf": dcf_res,
            "graham": graham_res,
            "ddm": ddm_res
        }
    }

def run_aries_valuation(ticker: str) -> dict:
    """Helper wrapper that loads data from yfinance and performs full valuation."""
    from src.engine.aries.data_loader import load_financial_data
    try:
        data = load_financial_data(ticker)
        val = evaluate_intrinsic_value(
            ticker=ticker,
            cmp=data["cmp"],
            fcf_0=data["fcf_0"],
            shares_outstanding=data["shares_outstanding"],
            total_debt=data["total_debt"],
            cash_equivalents=data["cash_equivalents"],
            eps=data["eps"],
            dividend_per_share=data["dividend_per_share"],
            growth_rate=data["growth_rate"],
            wacc=data["wacc"],
            cost_of_equity=data["cost_of_equity"],
            bond_yield=data["bond_yield"]
        )
        # Include data inputs in returned payload
        val["inputs"] = data
        return val
    except Exception as e:
        logger.error(f"Error executing Aries valuation for {ticker}: {e}")
        return {"status": "error", "message": str(e)}

