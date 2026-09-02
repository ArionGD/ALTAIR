import math
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import existing ALTAIR engine components
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker
from src.engine.swing.SwingScanner import classify_swing_setup
from src.engine.swing.TechnicalScore import calculate_technical_score
from src.cache.DailyCache import get_or_compute
from src.engine.sector.banking.BankScore import calculate_bank_score
from src.engine.sector.energy.EnergyScore import calculate_energy_score
from src.engine.sector.it.ITScore import calculate_it_score
from src.engine.scenario.OilShockEngine import get_oil_beta

router = APIRouter(prefix="/api/v1/altair", tags=["TradeLabs Master Integration"])

# Helper sector and sub-sector mappings for core universe
SECTOR_MAP = {
    "RELIANCE.NS": ("Energy", "Upstream"),
    "ONGC.NS": ("Energy", "Upstream"),
    "OIL.NS": ("Energy", "Upstream"),
    "IOC.NS": ("Energy", "Downstream"),
    "BPCL.NS": ("Energy", "Downstream"),
    "TCS.NS": ("IT", "Service"),
    "INFY.NS": ("IT", "Service"),
    "HCLTECH.NS": ("IT", "Service"),
    "WIPRO.NS": ("IT", "Service"),
    "TECHM.NS": ("IT", "Service"),
    "SBIN.NS": ("Banking", "Bank"),
    "HDFCBANK.NS": ("Banking", "Bank"),
    "ICICIBANK.NS": ("Banking", "Bank"),
    "AXISBANK.NS": ("Banking", "Bank"),
    "KOTAKBANK.NS": ("Banking", "Bank"),
    "ADANIPORTS.NS": ("Infra", "Transport_Logistics"),
    "ADANIGREEN.NS": ("Energy_Renewable", "Grid_Storage_Other"),
    "ADANIENT.NS": ("Infra", "Industrial_Capital_Goods"),
    "FCL.NS": ("Materials_Metals", "Chemicals"),
    "ITC.NS": ("Consumer_Tech_Beauty", "Beauty_Retail"),
}

class HoldingItem(BaseModel):
    ticker: str
    shares: int

class StressTestRequest(BaseModel):
    scenario: str
    portfolio: List[HoldingItem]

def _get_swing_data(ticker: str) -> Dict[str, Any]:
    """Computes technical indicators and fundamental scores for a ticker, using sector-specific metadata."""
    ranker = VulnerabilityRanker()
    sector, sub_sector = SECTOR_MAP.get(ticker, ("Infra", "Industrial_Capital_Goods"))
    row = {"ticker": ticker, "market": "IND", "sector": sector, "sub_sector": sub_sector, "pe_ratio": 0}
    
    # Calculate fundamental AVS and Technical Score
    fundamental = ranker.calculate_avs_score_v11(row)
    technical = calculate_technical_score(ticker, ranker.auditor)
    
    verdict = classify_swing_setup(fundamental['astra_strike_score'], technical['technical_score'])
    
    return {
        "ticker": ticker,
        "market": "IND",
        "sector": sector,
        "sub_sector": sub_sector,
        "astra_strike_score": fundamental['astra_strike_score'],
        "technical_score": technical['technical_score'],
        "close_price": technical.get('close_price', 0.0) or 100.0,  # Fallback if close is None
        "swing_verdict": verdict,
        "pe_ratio": fundamental.get('pe_ratio', 0.0) or 15.0,
    }

@router.get("/signals/radar")
async def get_signals_radar():
    """Daily Strike Radar: scans priority assets and returns actionable swing trade setups."""
    tickers = [
        "ADANIPORTS.NS", "ADANIGREEN.NS", "ADANIENT.NS", "FCL.NS", "ITC.NS",
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS"
    ]
    
    results = []
    for t in tickers:
        try:
            def _compute(ticker=t):
                return _get_swing_data(ticker)
            res, _ = get_or_compute(t, "radar_scan", _compute)
            results.append(res)
        except Exception as e:
            # Prevent single-ticker failures from breaking the entire scan
            print(f"[!] Warning: Failed to scan {t} for radar: {e}")
            
    signals = []
    # 1. Process strong setups
    for r in results:
        verdict = r.get("swing_verdict")
        entry = r.get("close_price", 100.0)
        strike = r.get("astra_strike_score", 50.0)
        tech = r.get("technical_score", 0.0)
        
        if verdict == "LONG SETUP":
            signals.append({
                "ticker": r["ticker"],
                "direction": "LONG",
                "entry_price": round(entry, 2),
                "target_price": round(entry * 1.15, 2),
                "stop_loss": round(entry * 0.93, 2),
                "conviction_score": int(min(95, max(65, 50 + tech/2 + (100 - strike)/3))),
                "rationale": f"Strong technical momentum crossover (score: {tech:.1f}) backed by a robust fundamental margin of safety (Astra Strike: {strike:.1f})."
            })
        elif verdict == "SHORT SETUP":
            signals.append({
                "ticker": r["ticker"],
                "direction": "SHORT",
                "entry_price": round(entry, 2),
                "target_price": round(entry * 0.85, 2),
                "stop_loss": round(entry * 1.07, 2),
                "conviction_score": int(min(95, max(65, 50 + abs(tech)/2 + strike/3))),
                "rationale": f"Downward momentum acceleration (score: {tech:.1f}) aligned with heightened balance sheet fragility (Astra Strike: {strike:.1f})."
            })
            
    # 2. Fallback check: if signals are sparse (< 3), relax parameters to supply best relative plays
    if len(signals) < 3:
        for r in results:
            if any(s["ticker"] == r["ticker"] for s in signals):
                continue
            entry = r.get("close_price", 100.0)
            strike = r.get("astra_strike_score", 50.0)
            tech = r.get("technical_score", 0.0)
            
            # Relaxed LONG rules
            if tech > 5 and strike < 50:
                signals.append({
                    "ticker": r["ticker"],
                    "direction": "LONG",
                    "entry_price": round(entry, 2),
                    "target_price": round(entry * 1.12, 2),
                    "stop_loss": round(entry * 0.94, 2),
                    "conviction_score": int(min(80, max(60, 50 + tech + (100 - strike)/4))),
                    "rationale": f"Moderate bullish momentum detected. Underpinned by stable fundamentals (Astra Strike: {strike:.1f})."
                })
            # Relaxed SHORT rules
            elif tech < -5 and strike > 50:
                signals.append({
                    "ticker": r["ticker"],
                    "direction": "SHORT",
                    "entry_price": round(entry, 2),
                    "target_price": round(entry * 0.88, 2),
                    "stop_loss": round(entry * 1.06, 2),
                    "conviction_score": int(min(80, max(60, 50 + abs(tech) + strike/4))),
                    "rationale": f"Underlying technical weakness observed. Elevated structural fragility (Astra Strike: {strike:.1f}) favors short entry."
                })
                
    return {"signals": signals[:6]}

@router.get("/sectors/scores")
async def get_sectors_scores():
    """Sector Diagnostic Matrix: aggregates average diagnostic metrics for Banking, Energy, and IT."""
    ranker = VulnerabilityRanker()
    
    # Core banks
    banks = ["SBIN.NS", "HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS"]
    bank_results = []
    for b in banks:
        try:
            res, _ = get_or_compute(b, "bank_score", lambda: calculate_bank_score(b, ranker.auditor))
            bank_results.append(res)
        except Exception as e:
            print(f"[!] BankScore fetch failed for {b}: {e}")
            
    # Core energy
    energy_cos = ["ONGC.NS", "OIL.NS", "RELIANCE.NS", "BPCL.NS"]
    energy_results = []
    for ec in energy_cos:
        try:
            res, _ = get_or_compute(ec, "energy_score", lambda: calculate_energy_score(ec, ranker.auditor))
            energy_results.append(res)
        except Exception as e:
            print(f"[!] EnergyScore fetch failed for {ec}: {e}")
            
    # Core IT
    it_cos = ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS"]
    it_results = []
    for ic in it_cos:
        try:
            res, _ = get_or_compute(ic, "it_score", lambda: calculate_it_score(ic, ranker.auditor))
            it_results.append(res)
        except Exception as e:
            print(f"[!] ITScore fetch failed for {ic}: {e}")

    # Helper function to categorize score
    def get_health(score: float) -> str:
        if score < 35: return "STRONG"
        if score < 50: return "STABLE"
        if score < 65: return "CAUTION"
        return "CRITICAL"

    # Aggregations
    # 1. Banking
    avg_bank_score = sum(r["bank_vulnerability_score"] for r in bank_results) / len(bank_results) if bank_results else 50.0
    avg_roa = sum(r["roa"] for r in bank_results if r.get("roa") is not None) / len(bank_results) if bank_results else 0.0
    avg_roe = sum(r["roe"] for r in bank_results if r.get("roe") is not None) / len(bank_results) if bank_results else 0.0
    avg_pb = sum(r["price_to_book"] for r in bank_results if r.get("price_to_book") is not None) / len(bank_results) if bank_results else 0.0
    
    # 2. Energy
    avg_energy_score = sum(r["energy_vulnerability_score"] for r in energy_results) / len(energy_results) if energy_results else 50.0
    avg_de = sum(r["debt_to_equity"] for r in energy_results if r.get("debt_to_equity") is not None) / len(energy_results) if energy_results else 0.0
    avg_margin = sum(r["operating_margin"] for r in energy_results if r.get("operating_margin") is not None) / len(energy_results) if energy_results else 0.0
    avg_cr = sum(r["current_ratio"] for r in energy_results if r.get("current_ratio") is not None) / len(energy_results) if energy_results else 0.0

    # 3. IT
    avg_it_score = sum(r["it_vulnerability_score"] for r in it_results) / len(it_results) if it_results else 50.0
    avg_it_margin = sum(r["operating_margin"] for r in it_results if r.get("operating_margin") is not None) / len(it_results) if it_results else 0.0
    avg_it_growth = sum(r["revenue_growth"] for r in it_results if r.get("revenue_growth") is not None) / len(it_results) if it_results else 0.0
    avg_it_net = sum(r["profit_margin"] for r in it_results if r.get("profit_margin") is not None) / len(it_results) if it_results else 0.0

    return {
        "sectors": [
            {
                "name": "Banking & BFSI",
                "key": "banking",
                "score": round(avg_bank_score, 1),
                "health": get_health(avg_bank_score),
                "metrics": {
                    "average_roa": round(avg_roa * 100, 2),  # Represent as %
                    "average_roe": round(avg_roe * 100, 2),  # Represent as %
                    "average_pb": round(avg_pb, 2)
                },
                "description": "Evaluates sector solvency via return ratios, leverage risk proxies, and valuation multiples."
            },
            {
                "name": "Energy & Infrastructure",
                "key": "energy",
                "score": round(avg_energy_score, 1),
                "health": get_health(avg_energy_score),
                "metrics": {
                    "average_debt_equity": round(avg_de, 1),
                    "average_operating_margin": round(avg_margin * 100, 2),  # %
                    "average_current_ratio": round(avg_cr, 2)
                },
                "description": "Evaluates capital capex efficiency, commodity price exposure, and free cash flow generation."
            },
            {
                "name": "IT & Services",
                "key": "it",
                "score": round(avg_it_score, 1),
                "health": get_health(avg_it_score),
                "metrics": {
                    "average_operating_margin": round(avg_it_margin * 100, 2),  # %
                    "average_revenue_growth": round(avg_it_growth * 100, 2),  # %
                    "average_profit_margin": round(avg_it_net * 100, 2)  # %
                },
                "description": "Evaluates asset-light operating margins, top-line growth trends, and wage inflation pressures."
            }
        ]
    }

@router.post("/scenario/stress-test")
async def run_scenario_stress_test(req: StressTestRequest):
    """Aladdin Macro Scenario Stress Tester: projects P&L returns and provides custom hedging recommendations."""
    if not req.portfolio:
        raise HTTPException(status_code=400, detail="Portfolio cannot be empty.")
        
    holdings_impact = []
    total_current_value = 0.0
    total_projected_value = 0.0
    
    for h in req.portfolio:
        ticker = h.ticker
        shares = h.shares
        
        try:
            # Fetch cached swing results to obtain latest price/sector metadata
            def _compute(ticker=ticker):
                return _get_swing_data(ticker)
            meta, _ = get_or_compute(ticker, "radar_scan", _compute)
        except Exception as e:
            # If yfinance metadata fails, use default fallback schema to prevent crash
            meta = {
                "close_price": 100.0,
                "sector": "Infra",
                "sub_sector": "Industrial_Capital_Goods",
                "astra_strike_score": 50.0,
                "pe_ratio": 15.0
            }
            print(f"[!] Warning: Falling back to static metadata for {ticker} during stress test: {e}")
            
        close_price = meta.get("close_price", 100.0)
        sector = meta.get("sector", "Infra")
        sub_sector = meta.get("sub_sector", "")
        strike = meta.get("astra_strike_score", 50.0)
        pe = meta.get("pe_ratio", 15.0)
        
        current_value = close_price * shares
        
        # Calculate impact based on scenario ID
        impact_pct = 0.0
        if req.scenario == "crude_oil_spike_20":
            beta = get_oil_beta(sector, sub_sector)
            # High-vulnerability stocks face magnified shocks
            impact_pct = -0.20 * beta * (1 + strike / 150.0)
        elif req.scenario == "fii_capital_outflow":
            # Outflows penalize high P/E multiples and banks
            pe_multiplier = max(0.5, min(2.5, pe / 25.0))
            sector_multiplier = 1.3 if sector in ["Banking", "BFSI"] else 1.0
            impact_pct = -0.10 * pe_multiplier * sector_multiplier
        elif req.scenario == "interest_rate_hike":
            # Shocks leveraged sectors (NBFCs/banks/infra), cash-rich services benefit
            if sector in ["Banking", "BFSI"]:
                impact_pct = -0.06 * (1 + strike / 100.0)
            elif sector == "IT":
                impact_pct = +0.02  # cash treasury yield benefit
            else:
                impact_pct = -0.04 * (1 + strike / 100.0)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported scenario: {req.scenario}")
            
        # Clip impact to realistic bounds (-50% to +50%)
        impact_pct = max(-0.50, min(0.50, impact_pct))
        
        projected_value = current_value * (1 + impact_pct)
        pnl = projected_value - current_value
        
        # Determine verdict
        if impact_pct <= -0.10:
            verdict = "HARD HIT — high scenario exposure"
        elif impact_pct < 0:
            verdict = "TEMPORARY CORRECTION — minor pressure"
        elif impact_pct >= 0.04:
            verdict = "BENEFICIARY — positive tailwinds"
        else:
            verdict = "RESILIENT — neutral impact"
            
        holdings_impact.append({
            "ticker": ticker,
            "shares": shares,
            "current_price": round(close_price, 2),
            "current_value": round(current_value, 2),
            "projected_change_pct": round(impact_pct * 100, 2),
            "projected_pnl_impact": round(pnl, 2),
            "verdict": verdict
        })
        
        total_current_value += current_value
        total_projected_value += projected_value
        
    total_pnl = total_projected_value - total_current_value
    total_return_pct = (total_pnl / total_current_value * 100) if total_current_value > 0 else 0.0
    
    # Custom hedging advice
    if total_return_pct < -5.0:
        if req.scenario == "crude_oil_spike_20":
            advice = "Your portfolio contains high-beta consumer, auto, or logistics holdings highly sensitive to fuel prices. Recommendation: allocate 15% to ICICI Gold ETF or upstream energy producers (e.g. ONGC.NS)."
        elif req.scenario == "fii_capital_outflow":
            advice = "Capital outflow is depressing high P/E assets. Recommendation: rotate 20% into defensive dividend yield monopolies (e.g. ITC.NS) or local infrastructure utilities."
        else:
            advice = "Leverage sensitivity is drag-scaling your returns. Recommendation: Trim vulnerable NBFC holdings and rotate into cash-rich IT services (TCS.NS) or liquid gold ETFs."
    else:
        advice = "Your portfolio exhibits strong structural resilience under this scenario. Continue maintaining your current allocations, and check weekly technical trends."

    return {
        "scenario": req.scenario,
        "total_current_value": round(total_current_value, 2),
        "total_projected_value": round(total_projected_value, 2),
        "projected_pnl_impact": round(total_pnl, 2),
        "projected_return_pct": round(total_return_pct, 2),
        "holdings_impact": holdings_impact,
        "hedging_advice": advice
    }
