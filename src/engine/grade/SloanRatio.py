from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd

class SloanRatioEngine:
    """
    ALTAIR: Earnings Quality Forensic Engine (The 'Sloan Ratio').
    Formula: (Net Income - Cash Flow from Ops) / Total Assets.
    
    A Score > 0.10 indicates 'Accrual-Heavy' earnings—meaning the 
    profits are on paper only, not in the bank. This is a primary 
    indicator of future share price cratering.
    """

    def __init__(self):
        self.auditor = SovereignAuditor()

    def calculate_sloan_ratio(self, ticker_symbol):
        print(f"[*] Auditing Earnings Quality (Sloan Ratio) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        
        try:
            # 1. Fetch Financials
            # We need the TTM or Latest Annual data
            financials = ticker.financials
            cashflow = ticker.cashflow
            balance_sheet = ticker.balance_sheet
            
            if financials.empty or cashflow.empty or balance_sheet.empty:
                print(f"    [!] Warning: Financial data incomplete for {ticker_symbol}.")
                return 0.0

            # 2. Extract Latest Year Data
            net_income = financials.loc['Net Income'].iloc[0]
            cfo = cashflow.loc['Cash Flow From Operating Activities'].iloc[0]
            total_assets = balance_sheet.loc['Total Assets'].iloc[0]
            
            # 3. Calculation
            sloan_ratio = (net_income - cfo) / total_assets
            
            # Normalization for ALTAIR Target Scoring
            # Score > 0.1 is critical
            print(f"    [+] Sloan Ratio: {round(sloan_ratio, 4)} ({'CRITICAL' if sloan_ratio > 0.1 else 'STABLE'})")
            return round(float(sloan_ratio), 4)

        except Exception as e:
            print(f"    [!] Sloan Audit Error for {ticker_symbol}: {e}")
            return 0.0

if __name__ == "__main__":
    engine = SloanRatioEngine()
    # Test on a known 'Growth' target
    engine.calculate_sloan_ratio("NYKAA.NS")
    # Test on a Cash Flow Machine
    engine.calculate_sloan_ratio("TCS.NS")
