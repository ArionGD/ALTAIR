"""
ALTAIR: IT Sector-Specific Forensic Engine.

Unlike Banking, Indian IT tickers' financial statements DO carry the
line items the generic 8-factor formula needs (EBIT, Total Debt, Total
Assets - confirmed present for TCS.NS), so the generic Altman Z / Beneish M
/ Piotroski F factors are directionally usable here. But IT/services
companies are asset-light and growth/margin-driven in a way those
industrial-forensic factors don't emphasize (they're built around balance-
sheet distress signals - inventory manipulation, leverage - that matter
less for a business with few physical assets and no inventory). This module
adds IT-specific signals (margin quality, revenue growth, profitability) as
a complement, not a wholesale replacement, since the underlying data
supports both.
"""


def calculate_it_score(ticker_symbol, auditor):
    """
    IT Vulnerability Score (0-100, higher = more fragile), from 4 factors:
      1. Margin quality (30%) - operating margin. IT services live and die
         on margin (wage inflation, pricing pressure, utilization) more than
         on balance-sheet leverage.
      2. Growth trend (30%) - revenue growth. Slowing/negative growth is the
         earliest fragility signal for a growth-priced IT/product name.
      3. Profitability (25%) - net profit margin, a check against companies
         that grow revenue but not earnings (a common product/SaaS pattern).
      4. Valuation (15%) - P/E, normalized same as the generic formula.
    """
    # get_ticker_object(...).info, not get_info() - see BankScore.py's note
    # on why get_info() (NSE-bridge routed, currently broken for .NS
    # tickers) doesn't carry these fields.
    info = auditor.get_ticker_object(ticker_symbol).info

    operating_margin = info.get('operatingMargins')
    revenue_growth = info.get('revenueGrowth')
    profit_margin = info.get('profitMargins')
    pe_ratio = info.get('trailingPE') or 0

    # 1. Margin quality (30%): operating margin < 10% is weak for IT services
    # (Tier-1 IT typically runs 20-25%).
    if operating_margin is None:
        margin_score = 50
    else:
        margin_score = max(0, min(100, (0.20 - operating_margin) / 0.20 * 100))

    # 2. Growth trend (30%): negative revenue growth is a real fragility
    # signal for a sector priced on growth.
    if revenue_growth is None:
        growth_score = 50
    else:
        growth_score = max(0, min(100, (0.10 - revenue_growth) / 0.25 * 100))

    # 3. Profitability (25%): net margin < 10% is thin for IT/product names.
    if profit_margin is None:
        profit_score = 50
    else:
        profit_score = max(0, min(100, (0.15 - profit_margin) / 0.15 * 100))

    # 4. Valuation (15%): same normalization as the generic formula.
    pe_score = min(max(pe_ratio, 0), 300) / 300 * 100

    it_vulnerability = (
        (margin_score * 0.30) + (growth_score * 0.30) +
        (profit_score * 0.25) + (pe_score * 0.15)
    )

    return {
        "operating_margin": operating_margin,
        "revenue_growth": revenue_growth,
        "profit_margin": profit_margin,
        "pe_ratio": pe_ratio,
        "it_vulnerability_score": round(it_vulnerability, 2),
    }
