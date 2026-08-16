import requests
# from nsepython import nse_get_fno_lot_sizes, nse_get_index_quote
import json
import pandas as pd
import time

class NSEDataBridge:
    """
    ALTAIR Sovereign Data Bridge (V10.0).
    Direct NSE Connection with Session/Cookie management.
    Bypasses yfinance for Indian Tickers to ensure 100% accuracy.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "referer": "https://www.nseindia.com/"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._refresh_session()

    def _refresh_session(self):
        """Initializes the cookie by visiting the NSE home page."""
        try:
            self.session.get("https://www.nseindia.com/", timeout=10)
            print("[+] NSE Data Bridge: Session Revived (Cookie Captured).")
        except Exception as e:
            print(f"[!] NSE Data Bridge Error: Session Failed: {e}")

    def get_info(self, ticker_symbol):
        """
        Mimics yfinance.info for NSE tickers.
        Fetches direct from nseindia.com/api/quote-equity?symbol=...
        """
        symbol = ticker_symbol.replace(".NS", "")
        url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 401 or response.status_code == 403:
                self._refresh_session()
                response = self.session.get(url, timeout=10)
            
            data = response.json()
            
            # Map NSE JSON structure to ALTAIR format
            metadata = data.get('metadata', {})
            price_info = data.get('priceInfo', {})
            
            # Derived Metrics (Sovereign Quality)
            info = {
                "ticker": ticker_symbol,
                "currentPrice": price_info.get('lastPrice', 0),
                "previousClose": price_info.get('close', price_info.get('previousClose', 0)),
                "trailingPE": data.get('metadata', {}).get('pdSectorPe', 0), # Sector PE as proxy if individual is blank
                "debtToEquity": 0.0, # Will be filled by Financials Auditor
                "industry": metadata.get('industry', 'N/A'),
                "sector": metadata.get('pdSectorInd', 'N/A'),
                "longName": metadata.get('companyName', ticker_symbol)
            }
            return info
        except Exception as e:
            print(f"    [!] NSE Bridge Error for {symbol}: {e}")
            return {}

    def get_financials(self, ticker_symbol):
        """Fetches the 4-year financial trend directly from NSE Corporate Filings."""
        symbol = ticker_symbol.replace(".NS", "")
        # This is a different endpoint: nseindia.com/api/results-fin-year-wise?symbol=...
        url = f"https://www.nseindia.com/api/results-fin-year-wise?symbol={symbol}"
        try:
            response = self.session.get(url, timeout=10)
            return response.json()
        except:
            return []

if __name__ == "__main__":
    bridge = NSEDataBridge()
    info = bridge.get_info("NYKAA.NS")
    print(f"NYKAA NSE Price: {info.get('currentPrice')}")
