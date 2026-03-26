import yfinance as yf
from src.engine.bridge.NSEDataBridge import NSEDataBridge

class SovereignAuditor:
    """
    ALTAIR: Universal Forensic Auditor (Data Router).
    Routes data requests to the most accurate source:
    - Indian Tickers (.NS): NSEDataBridge (Direct NSE API).
    - Global Tickers: yfinance (Fallback for US/Global).
    """

    def __init__(self):
        self.nse_bridge = NSEDataBridge()

    def get_info(self, ticker_symbol):
        """
        Universal Info Fetcher.
        Returns a dictionary with CMP, PE, and basic metadata.
        """
        if ticker_symbol.endswith(".NS") or ticker_symbol.endswith(".BO"):
            # Using NSE Direct API
            return self.nse_bridge.get_info(ticker_symbol)
        else:
            # Falling back to Global yfinance (Usually accurate for US)
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            return info

    def get_ticker_object(self, ticker_symbol):
        """
        Universal Ticker Object.
        For Indian symbols, we return a customized 'NSE-Proxy' object 
        that mimics yfinance functions (financials, balance_sheet).
        """
        if ticker_symbol.endswith(".NS"):
            # This is where we create the NSE-Proxy if we need complex analysis.
            # For now, let's keep it simple: fetch directly from Bridge.
            return yf.Ticker(ticker_symbol) # Fallback if we don't have full financial scrapers yet
        else:
            return yf.Ticker(ticker_symbol)

if __name__ == "__main__":
    auditor = SovereignAuditor()
    info = auditor.get_info("NYKAA.NS")
    print(f"Sovereign Audit Check (NYKAA): ₹{info.get('currentPrice')}")
