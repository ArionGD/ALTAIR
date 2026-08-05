"""
ALTAIR: Energy Sector-Specific Forensic Engine.

Energy names (both Upstream producers and Downstream distribution/refining)
are capital-intensive, structurally higher-leverage, and commodity-price
exposed in ways the generic 8-factor formula's thresholds don't reflect
well - e.g. Altman Z's leverage term and EbitdaLeverageEngine's "> 4.0x is a
Massive Red Flag" heuristic are tuned for asset-light/industrial names, not
capex-heavy energy infrastructure where higher structural debt is normal.

This module keeps using real financial-statement data (EBIT, Total Debt,
Total Assets - all confirmed present for Indian energy tickers, unlike
banking) but applies energy-appropriate weighting: leverage tolerance is
wider, margin resilience and free cash flow generation matter more (a sign
of capital discipline through commodity cycles), and current ratio matters
for capex-cycle liquidity.
"""


def calculate_energy_score(ticker_symbol, auditor):
    """
    Energy Vulnerability Score (0-100, higher = more fragile), from 5 factors:
      1. Leverage (25%) - Debt/Equity, energy-calibrated: energy infra
         structurally runs higher D/E than industrials, so the "danger"
         threshold is set wider (>150 D/E) than the generic formula's.
      2. Margin resilience (25%) - operating margin. Energy margins swing
         with commodity prices; persistently thin margins signal a name
         that won't survive a downturn.
      3. Liquidity (20%) - current ratio. Capex-heavy names need working
         capital headroom to fund the next capital cycle without distress
         financing.
      4. Cash generation (20%) - free cash flow relative to total assets.
         positive, sizeable FCF signals capital discipline; negative FCF
         funded by rising debt is the energy-sector distress pattern.
      5. Valuation (10%) - P/E, capped/normalized same as the generic
         formula's valuation factor.
    """
    # get_ticker_object(...).info, not get_info() - see BankScore.py's note
    # on why get_info() (NSE-bridge routed, currently broken for .NS
    # tickers) doesn't carry these fields.
    info = auditor.get_ticker_object(ticker_symbol).info

    debt_to_equity = info.get('debtToEquity')
    operating_margin = info.get('operatingMargins')
    current_ratio = info.get('currentRatio')
    free_cashflow = info.get('freeCashflow')
    total_assets_info = info.get('totalAssets')
    pe_ratio = info.get('trailingPE') or 0

    # 1. Leverage (25%): D/E > 150 is a real red flag for energy infra
    # (vs. the generic formula's tighter industrial-style thresholds).
    if debt_to_equity is None:
        leverage_score = 50
    else:
        leverage_score = max(0, min(100, debt_to_equity / 150 * 100))

    # 2. Margin resilience (25%): operating margin < 5% is thin for energy.
    if operating_margin is None:
        margin_score = 50
    else:
        margin_score = max(0, min(100, (0.15 - operating_margin) / 0.15 * 100))

    # 3. Liquidity (20%): current ratio < 1.0 means current liabilities
    # exceed current assets - a real short-term funding risk.
    if current_ratio is None:
        liquidity_score = 50
    else:
        liquidity_score = max(0, min(100, (1.2 - current_ratio) / 1.2 * 100))

    # 4. Cash generation (20%): FCF relative to assets. Ticker's balance
    # sheet total assets aren't always in `info`, so this falls back to a
    # neutral score if unavailable rather than fabricating a ratio.
    if free_cashflow is None or not total_assets_info:
        cash_score = 50
    else:
        fcf_to_assets = free_cashflow / total_assets_info
        cash_score = max(0, min(100, (0.03 - fcf_to_assets) / 0.10 * 100))

    # 5. Valuation (10%): same normalization as the generic formula.
    pe_score = min(max(pe_ratio, 0), 300) / 300 * 100

    energy_vulnerability = (
        (leverage_score * 0.25) + (margin_score * 0.25) +
        (liquidity_score * 0.20) + (cash_score * 0.20) + (pe_score * 0.10)
    )

    return {
        "debt_to_equity": debt_to_equity,
        "operating_margin": operating_margin,
        "current_ratio": current_ratio,
        "free_cashflow": free_cashflow,
        "pe_ratio": pe_ratio,
        "energy_vulnerability_score": round(energy_vulnerability, 2),
    }
