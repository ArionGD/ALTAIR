from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd

class ShortFloatEngine:
    """
    ALTAIR: Sovereign Trend Forensic Engine (The 'Short Float').
    Formula: (Shares Shorted / Float Shares) * 100.
    
    A Score > 10% indicates 'High Conviction' shorting by institutions.
    A Score > 20% indicates 'Short Squeeze Risk' (Danger zone).
    """

    def __init__(self, auditor=None):
        self.auditor = auditor or SovereignAuditor()

    def calculate_short_float(self, ticker_symbol):
        print(f"[*] Auditing Short Interest (Short Float) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        info = ticker.info
        
        # 1. Fetch Key Metrics
        # 'floatShares' is tricky in India (not always reported as 'float')
        # We use shortPercentOfFloat if available
        short_perc = info.get('shortPercentOfFloat', 0)
        
        # 2. Logic: If none reported, check total shares short vs float as fallback
        if not short_perc or short_perc == 0:
            shares_short = info.get('sharesShort', 0)
            float_shares = info.get('floatShares', 0)
            
            if shares_short and float_shares and float_shares > 0:
                short_perc = (shares_short / float_shares) * 100
            else:
                short_perc = 0.0 # Default/Null for India (often hidden)

        # 3. High-Interest Heuristic
        # Score > 10% is a confirmed 'Wolf' target.
        # Score > 20% is a 'Vigilante' squeeze risk.
        status = "NORMAL"
        if short_perc > 20: 
            status = "SQUEEZE RISK"
        elif short_perc > 10: 
            status = "HIGH CONVICTION"

        print(f"    [+] Short Float: {round(short_perc, 2)}% ({status})")
        return round(float(short_perc), 2)

if __name__ == "__main__":
    engine = ShortFloatEngine()
    # Test on a known short target
    engine.calculate_short_float("TSLA") # High Float usually
    # Test on an Indian target
    engine.calculate_short_float("NYKAA.NS")
