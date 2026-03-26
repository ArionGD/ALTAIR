from src.engine.hunter.SovereignAuditor import SovereignAuditor

class ZScoreEngine:
    """
    ALTAIR: Institutional Bankruptcy Predictor (Altman Z-Score)
    Formula: Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    
    Z-Score Interpretations:
    - > 3.0: Safe Zone (Strong Financials)
    - 1.8 to 3.0: Grey Zone (Caution Needed)
    - < 1.8: Distress Zone (High Bankruptcy Probability)
    """

    def __init__(self):
        self.auditor = SovereignAuditor()

    def calculate_altman_z(self, ticker_symbol):
        print(f"[*] Calculating Sovereign Z-Score for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        
        # 1. Fetch Key Balance Sheet & Income Data
        # We use a fallback logic in case some fields are missing
        balance_sheet = ticker.balance_sheet
        financials = ticker.financials
        info = ticker.info
        
        try:
            # A: Working Capital / Total Assets
            total_assets = balance_sheet.loc['Total Assets'].iloc[0]
            curr_assets = balance_sheet.loc['Current Assets'].iloc[0]
            curr_liabs = balance_sheet.loc['Current Liabilities'].iloc[0]
            A = (curr_assets - curr_liabs) / total_assets
            
            # B: Retained Earnings / Total Assets
            retained_earnings = balance_sheet.loc['Retained Earnings'].iloc[0]
            B = retained_earnings / total_assets
            
            # C: EBIT / Total Assets
            ebit = financials.loc['EBIT'].iloc[0]
            C = ebit / total_assets
            
            # D: Market Cap / Total Liabilities
            market_cap = info.get('marketCap', 0)
            total_liabs = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
            D = market_cap / total_liabs
            
            # E: Revenue / Total Assets
            revenue = financials.loc['Total Revenue'].iloc[0]
            E = revenue / total_assets
            
            # Final Altman Formula
            z_score = (1.2 * A) + (1.4 * B) + (3.3 * C) + (0.6 * D) + (1.0 * E)
            
            status = "Safe" if z_score > 3.0 else "Grey" if z_score > 1.8 else "DISTRESS"
            return round(z_score, 2), status
            
        except Exception as e:
            print(f"[!] Warning: Z-Score Audit failed for {ticker_symbol}. Trace: {e}")
            return None, "Incomplete Data"

if __name__ == "__main__":
    # Test on our 'Glass Pillars' (TSLA and Boeing)
    engine = ZScoreEngine()
    
    for t in ["TSLA", "BA", "STX"]:
        z, status = engine.calculate_altman_z(t)
        print(f"--- Ticker: {t} | Z-Score: {z} | Status: {status} ---")
