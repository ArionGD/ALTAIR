import pandas as pd
import os
import time
from datetime import datetime
from src.engine.hunter.SovereignAuditor import SovereignAuditor

class GlobalBilateralCollector:
    def __init__(self, base_dir="data/raw"):
        self.base_dir = base_dir
        self.auditor = SovereignAuditor()
        self.markets = {
            "US": {
                "BFSI": ["JPM", "BAC", "MS", "GS", "WFC", "BLK", "PYPL", "AXP", "SCHW", "C"],
                "IT_Service": ["ACN", "IBM", "INFY", "WIT", "CTSH", "EPAM", "GLW", "TEL", "IT", "GHI"],
                "Infra": ["CAT", "DE", "HON", "CSX", "UNP", "BA", "LMT", "RTX", "UPS", "FDX"],
                "Auto": ["TSLA", "F", "GM", "RIVN", "LCID", "TM", "HMC", "STLA", "VWAGY", "BMWYY"],
                "Energy_Renewable": ["NEE", "ENPH", "FSLR", "SEDG", "RUN", "BE", "TPIC", "WOLF", "HASI", "OSTE"],
                "Energy_Fossil": ["XOM", "CVX", "COP", "SLB", "EOG", "OXY", "PSX", "MPC", "VLO", "HES"],
                "Health": ["UNH", "PFE", "ABBV", "JNJ", "LLY", "MRK", "TMO", "ABT", "DHR", "BMY"],
                "Consumer_Tech_Beauty": ["UBER", "ABNB", "DASH", "MELI", "EL", "ULTA", "COTY", "PATH", "SNOW", "PLTR"]
            },
            "IND": {
                "BFSI": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "BAJFINANCE.NS", "HDFC.NS", "LICHSGFIN.NS", "RELIANCE.NS", "CHOLAFIN.NS"],
                "IT_Service": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "LTIM.NS", "TECHM.NS", "MPHASIS.NS", "COFORGE.NS", "PERSISTENT.NS", "TATAELXSI.NS"],
                "Infra": ["LT.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ULTRACEMCO.NS", "GRASIM.NS", "ABB.NS", "SIEMENS.NS", "BEL.NS", "HAL.NS", "DLF.NS"],
                "Auto": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "ASHOKLEY.NS", "TVSMOTOR.NS", "BHARATFORG.NS", "MRF.NS"],
                "Energy_Renewable": ["ADANIGREEN.NS", "SUZLON.NS", "TATAPOWER.NS", "JSWENERGY.NS", "NHPC.NS", "SJVN.NS", "IREDA.NS", "RECLTD.NS", "PFC.NS", "BORORENEW.NS"],
                "Energy_Fossil": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "COALINDIA.NS", "BPCL.NS", "IOC.NS", "GAIL.NS", "OIL.NS", "PETRONET.NS", "HINDPETRO.NS"],
                "Health": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "APOLLOHOSP.NS", "DIVISLAB.NS", "MANKIND.NS", "MAXHEALTH.NS", "LUPIN.NS", "AUROPHARMA.NS", "GLAND.NS"],
                "Consumer_Tech_Beauty": ["ZOMATO.NS", "PAYTM.NS", "NYKAA.NS", "POLICYBZR.NS", "DELHIVERY.NS", "CARTRADE.NS", "MAPMYINDIA.NS", "HONASA.NS", "MAMAEARTH.NS", "FSN.NS"]
            }
        }

    def fetch_metrics(self, ticker_symbol):
        print(f"[*] Auditing {ticker_symbol} (Sovereign Flow)...")
        info = self.auditor.get_info(ticker_symbol)
        
        # Cross-Market Normalization (NSE Quote API vs yf.info)
        pe = info.get('trailingPE', info.get('pdSectorPe', 0))
        price = info.get('currentPrice', info.get('previousClose', 0))
        
        return {
            "ticker": ticker_symbol,
            "pe_ratio": pe,
            "current_price": price,
            "industry": info.get('industry', 'N/A')
        }

    def run_global_audit(self):
        for market, sectors in self.markets.items():
            print(f"[*] Auditing Market: {market}...")
            for sector, tickers in sectors.items():
                print(f"    - Sector: {sector}...")
                sector_data = []
                for t in tickers:
                    try:
                        data = self.fetch_metrics(t)
                        sector_data.append(data)
                        time.sleep(1) # Rate limit protection
                    except Exception as e:
                        print(f"      [!] Warning: Failed on {t}: {e}")

                df = pd.DataFrame(sector_data)
                path = os.path.join(self.base_dir, market, sector, f"{market}_{sector}_vulnerability.csv")
                
                # Ensure the path exists
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                df.to_csv(path, index=False)
                print(f"    [+] {sector} Saved.")

if __name__ == "__main__":
    collector = GlobalBilateralCollector()
    collector.run_global_audit()
