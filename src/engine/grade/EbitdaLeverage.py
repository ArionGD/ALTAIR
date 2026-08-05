from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd

class EbitdaLeverageEngine:
    """
    ALTAIR: Debt Servicing Forensic Engine.
    Tracks 'Debt-to-EBITDA' ratio—the primary metric used by bondholders and 
    institutions to detect bankruptcy probability.
    
    A ratio > 4.0 is a Massive Red Flag (The 'Sacrifice' Zone).
    """

    def __init__(self, auditor=None):
        self.auditor = auditor or SovereignAuditor()

    def calculate_debt_to_ebitda(self, ticker_symbol):
        print(f"[*] Auditing EBITDA Leverage (Debt/EBITDA) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        info = ticker.info
        
        # 1. Fetch Core Metrics
        total_debt = info.get('totalDebt', 0)
        ebitda = info.get('ebitda', 0)
        
        # 2. Logic: Years to pay off debt via earnings
        if ebitda is None or ebitda <= 0:
            # If they have debt but NO earnings, vulnerability is maximum.
            if total_debt and total_debt > 0:
                print(f"    [!] Critical: Negative EBITDA with Debt. Vulnerability Maxed.")
                return 10.0 # Heuristic 'Dangerous' ratio
            return 0.0 # No debt, no earnings (Shell company)

        ratio = total_debt / ebitda
        
        # 3. High-Leverage Heuristic
        # In India, many high-growth cos hide leverage in subsidiaries. 
        # We cap the ratio at 15.0 for normalization.
        normalized_ratio = min(ratio, 15.0)
        
        print(f"    [+] Debt-to-EBITDA: {round(normalized_ratio, 2)}x")
        return round(float(normalized_ratio), 2)

if __name__ == "__main__":
    engine = EbitdaLeverageEngine()
    # Test on a known high-leverage target
    engine.calculate_debt_to_ebitda("ADANIGREEN.NS")
    # Test on an Iron Fortress
    engine.calculate_debt_to_ebitda("TCS.NS")
