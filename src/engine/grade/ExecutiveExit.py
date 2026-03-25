import yfinance as yf
import pandas as pd

class ExecutiveExitEngine:
    """
    ALTAIR: Institutional 'Founder Dump' Auditor.
    Tracks if the ship's captains are in the lifeboats.
    - Negative Change = Founders are selling (Strike Signal).
    - Positive/Zero = Founders are holding (Resilient).
    """

    def calculate_founder_risk(self, ticker_symbol):
        print(f"[*] Auditing Executive Integrity for {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch Major Holder Data
        # yfinance reports 'Held by Insiders' and 'Held by Institutions'
        info = ticker.info
        
        insider_perc = info.get('heldByInsiders', 0)
        inst_perc = info.get('heldByInstitutions', 0)
        
        # 2. Heuristic for High-Risk Exit (Placeholder for historical diff)
        # Note: True historical diff requires scraping SEC Form 4 (US) or NSE filings (IND).
        # We start with the absolute 'Insider Density'. 
        held_by_insiders = insider_perc * 100 # Convert to percentage
        
        # Risk Logic: 
        # If Insiders hold < 5% of a 'Founder-Led' company, it signals total exit.
        # If Insiders hold > 50%, they are 'Too Heavy' and cannot liquidate fast (Risk).
        
        is_founder_exited = True if held_by_insiders < 3.0 else False
        
        return round(held_by_insiders, 2), is_founder_exited

if __name__ == "__main__":
    engine = ExecutiveExitEngine()
    for t in ["NYKAA.NS", "TSLA", "ZOMATO.NS"]:
        p, exited = engine.calculate_founder_risk(t)
        print(f"--- Ticker: {t} | Insider Holding: {p}% | Exited: {exited} ---")
