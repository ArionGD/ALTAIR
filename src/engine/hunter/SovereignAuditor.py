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
        # Per-ticker yf.Ticker() cache. All 7 scoring engines (ZScore,
        # EbitdaLeverage, Sloan, ROIC, Beneish, Piotroski, ShortFloat) each
        # ask for the same ticker's balance_sheet/financials/cashflow/info
        # independently; without this cache every one of them created its
        # own yf.Ticker() and re-fetched from the network from scratch,
        # turning 1 ticker's worth of data into ~7 redundant network calls.
        self._ticker_cache = {}

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
            return self.get_ticker_object(ticker_symbol).info

    def get_ticker_object(self, ticker_symbol):
        """
        Universal Ticker Object.
        For Indian symbols, we return a customized 'NSE-Proxy' object
        that mimics yfinance functions (financials, balance_sheet).
        Cached per ticker so repeated calls (e.g. from each scoring engine)
        reuse the same object instead of re-fetching over the network.
        """
        if ticker_symbol not in self._ticker_cache:
            # Both branches currently return a plain yf.Ticker() (the NSE-proxy
            # is a placeholder for future work), but cache lookup happens
            # before the branch so that stays true regardless of which path runs.
            self._ticker_cache[ticker_symbol] = yf.Ticker(ticker_symbol)
        return self._ticker_cache[ticker_symbol]

if __name__ == "__main__":
    auditor = SovereignAuditor()
    info = auditor.get_info("NYKAA.NS")
    print(f"Sovereign Audit Check (NYKAA): ₹{info.get('currentPrice')}")
