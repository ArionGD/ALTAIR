from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd
import numpy as np

class BeneishMScoreEngine:
    """
    ALTAIR: Manipulation Forensic Engine (The 'Beneish M-Score').
    A 8-variable regression model to detect earnings fraud.
    
    Score > -1.78 = Likely Manipulator (The Fake Pillar).
    Score < -2.22 = Not a Manipulator (Real Operations).
    """

    def __init__(self, auditor=None):
        self.auditor = auditor or SovereignAuditor()

    def calculate_m_score(self, ticker_symbol):
        print(f"[*] Auditing Manipulation (Beneish M-Score) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        
        try:
            # 1. Fetch Financials (Last 2 years)
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            if len(financials.columns) < 2:
                print(f"    [!] Warning: Financial history insufficient for {ticker_symbol}.")
                return -2.5 # Negative/Safe default
            
            # --- Key Variables ---
            # yfinance can have a row present in the index but NaN for a
            # specific period's cell (seen on IOC.NS: 'Selling General And
            # Administration' row exists, latest-year value is NaN) - a bare
            # "if 'X' in index else default" guard misses that, and a NaN
            # here silently propagates through every ratio below into the
            # final m_score, which then poisons the whole weighted AVS sum
            # in VulnerabilityRanker (any NaN input -> NaN sum). _safe()
            # normalizes both "row missing" and "row present but NaN" to the
            # same fallback default.
            def _safe(value, default=0):
                return default if pd.isna(value) else value

            sales = _safe(financials.loc['Total Revenue'].iloc[0])
            prev_sales = _safe(financials.loc['Total Revenue'].iloc[1])
            receivables = _safe(balance_sheet.loc['Accounts Receivable'].iloc[0]) if 'Accounts Receivable' in balance_sheet.index else 0
            prev_receivables = _safe(balance_sheet.loc['Accounts Receivable'].iloc[1]) if 'Accounts Receivable' in balance_sheet.index and len(balance_sheet.columns) > 1 else 0
            gp = _safe(financials.loc['Gross Profit'].iloc[0])
            prev_gp = _safe(financials.loc['Gross Profit'].iloc[1])
            assets = _safe(balance_sheet.loc['Total Assets'].iloc[0])
            prev_assets = _safe(balance_sheet.loc['Total Assets'].iloc[1])
            dep = _safe(financials.loc['Depreciation And Amortization'].iloc[0]) if 'Depreciation And Amortization' in financials.index else 0
            prev_dep = _safe(financials.loc['Depreciation And Amortization'].iloc[1]) if 'Depreciation And Amortization' in financials.index and len(financials.columns) > 1 else dep
            ppe = _safe(balance_sheet.loc['Net PPE'].iloc[0], default=1000) if 'Net PPE' in balance_sheet.index else 1000
            prev_ppe = _safe(balance_sheet.loc['Net PPE'].iloc[1], default=1000) if 'Net PPE' in balance_sheet.index and len(balance_sheet.columns) > 1 else 1000
            sga = _safe(financials.loc['Selling General And Administration'].iloc[0]) if 'Selling General And Administration' in financials.index else 0
            prev_sga = _safe(financials.loc['Selling General And Administration'].iloc[1]) if 'Selling General And Administration' in financials.index and len(financials.columns) > 1 else 0
            cfo = _safe(cashflow.loc['Operating Cash Flow'].iloc[0])

            # --- The indices (8-Ratio) ---
            dsri = (receivables/sales) / (prev_receivables/prev_sales) if prev_receivables and prev_sales else 1
            gmi = (prev_gp/prev_sales) / (gp/sales) if gp and sales else 1
            aqi = (1 - (receivables + ppe)/assets) / (1 - (prev_receivables + prev_ppe)/prev_assets) if prev_assets else 1
            sgi = sales/prev_sales if prev_sales else 1
            depi = (prev_dep/prev_ppe) / (dep/ppe) if dep and ppe else 1
            sgai = (sga/sales) / (prev_sga/prev_sales) if prev_sales and sales and prev_sga else 1
            tata = (financials.loc['Net Income'].iloc[0] - cfo) / assets
            
            # --- Final Score Regression ---
            m_score = -4.84 + 0.92 * dsri + 0.528 * gmi + 0.404 * aqi + 0.892 * sgi + 0.115 * depi - 0.172 * sgai + 4.679 * tata
            
            status = "REAL GROWTH"
            if m_score > -1.78: status = "MANIPULATOR"
            
            print(f"    [+] Beneish M-Score: {round(m_score, 2)} ({status})")
            return round(m_score, 2)

        except Exception as e:
            print(f"    [!] M-Score Audit Error for {ticker_symbol}: {e}")
            return -2.5

if __name__ == "__main__":
    engine = BeneishMScoreEngine()
    engine.calculate_m_score("NYKAA.NS")
    engine.calculate_m_score("ADANIENT.NS")
