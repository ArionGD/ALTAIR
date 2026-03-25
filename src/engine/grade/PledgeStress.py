import yfinance as yf

class PledgeStressEngine:
    """
    ALTAIR: Margin Call Pressure Module.
    Tracks the 'Hidden Debt' of the founders.
    A high pledge percentage = Sudden Liquidation Risk.
    """

    def calculate_margin_call_pressure(self, ticker_symbol):
        print(f"[*] Analyzing Pledge-Stress (Margin Call Risk) for {ticker_symbol}...")
        
        # Note: In India, Pledge % is a mandatory filing to NSE/BSE.
        # In US, it is more hidden but can be derived from institutional holdings.
        # For ALTAIR V3, we assume a stress factor based on institutional vs insider density.
        
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Derived Metric: How much of the float is controlled by 'Active Debt'
        # A high Institutional Density with no Insider Density often implies 'Debt Pressure'.
        insider_hold = info.get('heldByInsiders', 0)
        inst_hold = info.get('heldByInstitutions', 0)
        
        # Pledge Proxy: (Institutions / Insiders) * Beta
        # If institutions hold 90% and Insiders only 5%, the founder has zero control.
        risk_ratio = (inst_hold / (insider_hold if insider_hold > 0 else 0.01))
        
        pledge_risk = min(risk_ratio * 10, 100) # Normailzed to 100
        
        return round(pledge_risk, 2)

if __name__ == "__main__":
    engine = PledgeStressEngine()
    print(f"Margin Call Pressure (NYKAA.NS): {engine.calculate_margin_call_pressure('NYKAA.NS')}")
    print(f"Margin Call Pressure (AAPL): {engine.calculate_margin_call_pressure('AAPL')}")
