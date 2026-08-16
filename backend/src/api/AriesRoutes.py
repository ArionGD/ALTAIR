from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.engine.aries.aries_engine import evaluate_intrinsic_value, run_aries_valuation

router = APIRouter(prefix="/api/v1/aries", tags=["Aries Intrinsic Valuation"])

class CustomValuationRequest(BaseModel):
    ticker: str
    cmp: float
    fcf_0: float
    shares_outstanding: float
    total_debt: float
    cash_equivalents: float
    eps: float
    dividend_per_share: float
    growth_rate: float        # growth as decimal, e.g., 0.10 for 10%
    wacc: float               # wacc as decimal, e.g., 0.10 for 10%
    cost_of_equity: float     # cost of equity as decimal, e.g., 0.12 for 12%
    bond_yield: float          # 10Y Bond yield as percentage, e.g., 4.0 for 4%

@router.get("/evaluate/{ticker}")
async def evaluate_ticker(ticker: str):
    """Fetches key metrics for a given ticker from yfinance and performs 
    intrinsic valuation using DCF, Revised Graham, and DDM models.
    """
    res = run_aries_valuation(ticker)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/evaluate/custom")
async def evaluate_custom(req: CustomValuationRequest):
    """Performs intrinsic valuation using manually overridden input parameters."""
    try:
        res = evaluate_intrinsic_value(
            ticker=req.ticker,
            cmp=req.cmp,
            fcf_0=req.fcf_0,
            shares_outstanding=req.shares_outstanding,
            total_debt=req.total_debt,
            cash_equivalents=req.cash_equivalents,
            eps=req.eps,
            dividend_per_share=req.dividend_per_share,
            growth_rate=req.growth_rate,
            wacc=req.wacc,
            cost_of_equity=req.cost_of_equity,
            bond_yield=req.bond_yield
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
