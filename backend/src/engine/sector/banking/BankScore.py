"""
ALTAIR: Banking Sector-Specific Forensic Engine.

The generic 8-factor formula (Altman Z, Beneish M, Piotroski F - see
VulnerabilityRanker.calculate_avs_score_v11) is built for manufacturing/
retail-style financial statements: 'EBIT', 'Current Assets', 'Current
Liabilities', 'Gross Profit', 'Cost Of Revenue', 'Net PPE'. Bank balance
sheets don't report these in a comparable way (a bank's "inventory" is loans,
its "revenue" is net interest income), so every one of those factors was
silently failing/defaulting identically for every bank - see the bug this
sector module was written to fix (all banks showing F-Score=4, M-Score=-2.50
identically in the Sector Ranker).

The real bank-analyst ratios (NPA ratio, CASA ratio, Capital Adequacy Ratio,
Net Interest Margin, Provision Coverage Ratio) come from RBI regulatory
filings/investor presentations - NOT from yfinance's generic financials API,
confirmed by direct inspection (get_info() returns no NPA/CASA/CAR/NIM/PCR
fields for NSE bank tickers). Getting those would need either scraping a
site like screener.in (no official API, ToS unverified) or a paid data
provider - out of scope for now.

This is a deliberate, disclosed substitution: bank-relevant signals that ARE
reliably fetchable from yfinance's `info` dict, standing in for the ratios a
real bank credit analyst would prefer. Revisit if/when a real NPA/CASA/CAR
data source is wired in.
"""


def calculate_bank_score(ticker_symbol, auditor):
    """
    Bank Vulnerability Score (0-100, higher = more fragile), from 5 factors:
      1. Asset efficiency (25%) - ROA. Banks run thin ROA by nature (1-2%
         is normal); a low/negative ROA signals the bank isn't earning on
         its asset base, a real distress signal.
      2. Capital thinness proxy (20%) - abnormally high ROE combined with
         low ROA suggests leverage-driven returns (thin equity cushion
         relative to assets), not efficiency - a red flag banking analysts
         watch for even without a direct CAR figure.
      3. Market confidence (20%) - Price-to-Book. A bank trading persistently
         below book value signals the market doubts the stated book value of
         its loan book (an indirect proxy for asset-quality/NPA concerns
         that would otherwise come from the NPA ratio itself).
      4. Liquidity buffer (20%) - Cash-to-Debt ratio. Not a CASA ratio, but
         a directionally similar liquidity-cushion signal from data that IS
         available.
      5. Earnings trend (15%) - revenue growth (proxy for net interest
         income trend). Shrinking revenue is an early-warning signal.
    """
    # get_ticker_object(...).info (yfinance's full info dict), NOT
    # get_info() - the latter routes .NS tickers through NSEDataBridge,
    # which only returns a thin price/PE dict (and is currently broken -
    # see the NSE bot-block note in NSEDataBridge.py) and has none of the
    # ROA/ROE/priceToBook/totalCash/totalDebt fields this formula needs.
    info = auditor.get_ticker_object(ticker_symbol).info

    roa = info.get('returnOnAssets')
    roe = info.get('returnOnEquity')
    price_to_book = info.get('priceToBook')
    total_cash = info.get('totalCash') or 0
    total_debt = info.get('totalDebt') or 0
    revenue_growth = info.get('revenueGrowth')

    # 1. Asset efficiency (25%): ROA < 0.5% is weak for a bank, > 1.5% is strong.
    if roa is None:
        roa_score = 50  # neutral - no data
    else:
        roa_score = max(0, min(100, (0.015 - roa) / 0.015 * 100))

    # 2. Capital thinness proxy (20%): high ROE + low ROA = leverage-driven,
    # not efficiency-driven. ROE/ROA ratio above ~15x is a thin-capital flag
    # (typical well-capitalized bank ROE/ROA sits around 8-12x).
    if roa is None or roe is None or roa <= 0:
        thinness_score = 50
    else:
        leverage_multiple = roe / roa
        thinness_score = max(0, min(100, (leverage_multiple - 8) / 12 * 100))

    # 3. Market confidence (20%): P/B < 1.0 signals the market doesn't trust
    # stated book value (asset-quality doubt); P/B > 2.5 is richly valued.
    if price_to_book is None:
        pb_score = 50
    else:
        pb_score = max(0, min(100, (1.5 - price_to_book) / 1.5 * 100))

    # 4. Liquidity buffer (20%): low cash relative to debt is a vulnerability.
    if total_debt <= 0:
        liquidity_score = 0 if total_cash > 0 else 50
    else:
        cash_to_debt = total_cash / total_debt
        liquidity_score = max(0, min(100, (0.3 - cash_to_debt) / 0.3 * 100))

    # 5. Earnings trend (15%): shrinking revenue is an early-warning signal.
    if revenue_growth is None:
        growth_score = 50
    else:
        growth_score = max(0, min(100, (0.05 - revenue_growth) / 0.20 * 100))

    bank_vulnerability = (
        (roa_score * 0.25) + (thinness_score * 0.20) + (pb_score * 0.20) +
        (liquidity_score * 0.20) + (growth_score * 0.15)
    )

    return {
        "roa": roa,
        "roe": roe,
        "price_to_book": price_to_book,
        "cash_to_debt": (total_cash / total_debt) if total_debt > 0 else None,
        "revenue_growth": revenue_growth,
        "bank_vulnerability_score": round(bank_vulnerability, 2),
    }
