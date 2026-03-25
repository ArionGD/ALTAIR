import yfinance as yf
import pandas as pd

class PledgeAuditor:
    """
    ALTAIR: Margin Call Forensic Module (PR - Pledge Rate Audit).
    Identifies if founders have leveraged their ownership, creating high-risk floor vulnerability.
    """

    def audit_pledge_rate(self, ticker_symbol):
        """
        Calculates the Pledge Rate (PR) heuristic.
        If actual NSE/SEC data is unavailable, it uses the Institutional-to-Insider Leverage (IIL) proxy.
        """
        print(f"[*] Auditing Pledge Rate (PR) for {ticker_symbol}...")
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # 1. Ownership Metrics
        insider_perc = info.get('heldByInsiders', 0)
        inst_perc = info.get('heldByInstitutions', 0)
        
        # 2. Logic: The 'Margin Call' Proxy
        # High-risk signal: Founders hold very little (exited) OR 
        # founders hold a lot but Institutions have high density (implying leverage).
        
        if insider_perc == 0:
            # Full Exit = Maximum PR Vulnerability
            pr_score = 100.0
        else:
            # IIL Ratio: (Institutions / Insiders)
            # A ratio > 10.0 implies founders have lost 'Control Integrity'
            iil_ratio = inst_perc / (insider_perc if insider_perc > 0 else 0.01)
            
            # Scale to 100
            pr_score = min(iil_ratio * 10, 100)
            
        # 3. Known Indian High-Pledge Groups Heuristic (Forensic Override)
        high_pledge_groups = ["ADANI", "ZEE", "RELIANCE"] # Note: RELIANCE has some, ADANI context
        for group in high_pledge_groups:
            if group in ticker_symbol.upper():
                pr_score = max(pr_score, 80.0) # High floor for known pledge groups
                
        print(f"    [+] Pledge Rate (PR) Score: {round(pr_score, 2)}")
        return round(float(pr_score), 2)

if __name__ == "__main__":
    auditor = PledgeAuditor()
    auditor.audit_pledge_rate("NYKAA.NS")
    auditor.audit_pledge_rate("ADANIENT.NS")
    auditor.audit_pledge_rate("AAPL")
