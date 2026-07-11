import pandas as pd
import os
import time
from datetime import datetime
from src.engine.hunter.SovereignAuditor import SovereignAuditor

class GlobalBilateralCollector:
    """
    ALTAIR Universe Collector.
    Fixed universe: market -> sector -> sub_sector -> 10 tickers.
    10 sectors x 2 sub-sectors x 10 tickers = 200 tickers per market
    (US + IND = 400 total). Sub-sectors let scenario exposure (e.g.
    oil-shock beta) vary within a sector instead of being one flat
    sector-wide number.
    """
    def __init__(self, base_dir="data/raw"):
        self.base_dir = base_dir
        self.auditor = SovereignAuditor()
        self.markets = {
            "US": {
                "BFSI": {
                    "Money_Center_Banks": ["JPM", "BAC", "WFC", "C", "USB", "PNC", "TFC", "STT", "BK", "KEY"],
                    "Investment_Markets": ["GS", "MS", "SCHW", "BLK", "AXP", "PYPL", "COF", "ICE", "CME", "SPGI"],
                },
                "IT_Service": {
                    "Global_IT_Services": ["ACN", "IBM", "CTSH", "EPAM", "GLW", "TEL", "DXC", "CDW", "FIS", "FISV"],
                    "Indian_Offshore_ADR": ["INFY", "WIT", "IT", "GHI", "SYNH", "EXLS", "WNS", "GLOB", "TASK", "DAVA"],
                },
                "Infra": {
                    "Industrial_Capital_Goods": ["CAT", "DE", "HON", "ETN", "EMR", "ITW", "PH", "DOV", "ROK", "XYL"],
                    "Transport_Logistics": ["CSX", "UNP", "UPS", "FDX", "NSC", "JBHT", "ODFL", "CHRW", "XPO", "LSTR"],
                },
                "Auto": {
                    "EV_Growth": ["TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "FSR", "CHPT", "BLNK", "GOEV"],
                    "Legacy_ICE": ["F", "GM", "TM", "HMC", "STLA", "VWAGY", "BMWYY", "RACE", "MGA", "LEA"],
                },
                "Energy_Renewable": {
                    "Solar": ["ENPH", "FSLR", "SEDG", "RUN", "SHLS", "ARRY", "CSIQ", "JKS", "NOVA", "MAXN"],
                    "Grid_Storage_Other": ["NEE", "BE", "TPIC", "WOLF", "HASI", "OSTE", "PLUG", "FLNC", "AMPS", "STEM"],
                },
                "Energy_Fossil": {
                    "Integrated_Majors": ["XOM", "CVX", "COP", "OXY", "HES", "EQT", "DVN", "MRO", "APA", "CTRA"],
                    "Refining_Services": ["SLB", "EOG", "PSX", "MPC", "VLO", "HAL", "BKR", "FANG", "WMB", "KMI"],
                },
                "Health": {
                    "Pharma": ["PFE", "ABBV", "JNJ", "LLY", "MRK", "BMY", "GILD", "VRTX", "REGN", "ZTS"],
                    "Providers_Devices": ["UNH", "TMO", "ABT", "DHR", "CVS", "CI", "HUM", "MDT", "SYK", "BSX"],
                },
                "Consumer_Tech_Beauty": {
                    "Consumer_Internet": ["UBER", "ABNB", "DASH", "MELI", "PATH", "SNOW", "PLTR", "ETSY", "W", "CHWY"],
                    "Beauty_Retail": ["EL", "ULTA", "COTY", "ELF", "IPAR", "OLPX", "PRDO", "TPX", "NWL", "HELE"],
                },
                "Telecom_Media": {
                    "Telecom_Carriers": ["T", "VZ", "TMUS", "CHTR", "CMCSA", "LUMN", "USM", "TDS", "ATUS", "LBRDK"],
                    "Media_Streaming": ["DIS", "NFLX", "WBD", "PARA", "FOXA", "ROKU", "LYV", "SIRI", "FUBO", "AMCX"],
                },
                "Materials_Metals": {
                    "Steel_Mining": ["NUE", "STLD", "CLF", "X", "MP", "AA", "CENX", "SCCO", "FCX", "TX"],
                    "Chemicals": ["DOW", "LYB", "DD", "EMN", "CE", "ALB", "FMC", "OLN", "ASH", "HUN"],
                },
            },
            "IND": {
                "BFSI": {
                    "Private_Banks": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS", "RBLBANK.NS", "BANDHANBNK.NS", "AUBANK.NS"],
                    "PSU_NBFC": ["SBIN.NS", "BAJFINANCE.NS", "LICHSGFIN.NS", "CHOLAFIN.NS", "PNB.NS", "BANKBARODA.NS", "RECLTD.NS", "CANBK.NS", "UNIONBANK.NS", "MUTHOOTFIN.NS"],
                },
                "IT_Service": {
                    "Tier1_IT": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "LTIM.NS", "TECHM.NS", "LTTS.NS", "MINDTREE.NS", "OFSS.NS", "HEXAWARE.NS"],
                    "Tier2_IT": ["MPHASIS.NS", "COFORGE.NS", "PERSISTENT.NS", "TATAELXSI.NS", "CYIENT.NS", "ZENSARTECH.NS", "SONATSOFTW.NS", "NEWGEN.NS", "INTELLECT.NS", "BSOFT.NS"],
                },
                "Infra": {
                    "Construction_Cement": ["LT.NS", "ULTRACEMCO.NS", "GRASIM.NS", "AMBUJACEM.NS", "SHREECEM.NS", "DLF.NS", "ACC.NS", "JKCEMENT.NS", "RAMCOCEM.NS", "DALBHARAT.NS"],
                    "Capital_Goods_Defense": ["ADANIENT.NS", "ADANIPORTS.NS", "ABB.NS", "SIEMENS.NS", "BEL.NS", "HAL.NS", "CGPOWER.NS", "BHEL.NS", "THERMAX.NS", "MAZDOCK.NS"],
                },
                "Auto": {
                    "Passenger_Two_Wheeler": ["TATAMOTORS.NS", "MARUTI.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS", "M&M.NS", "TVSMOTOR.NS", "TIINDIA.NS", "ESCORTS.NS", "FORCEMOT.NS"],
                    "Commercial_Ancillary": ["ASHOKLEY.NS", "BHARATFORG.NS", "MRF.NS", "MOTHERSON.NS", "BALKRISIND.NS", "EXIDEIND.NS", "AMARAJABAT.NS", "SUNDRMFAST.NS", "BOSCHLTD.NS", "APOLLOTYRE.NS"],
                },
                "Energy_Renewable": {
                    "Green_Generation": ["ADANIGREEN.NS", "SUZLON.NS", "TATAPOWER.NS", "JSWENERGY.NS", "NHPC.NS", "SJVN.NS", "INOXWIND.NS", "BHEL.NS", "ORIENTGREEN.NS", "WEBSOL.NS"],
                    "Financing_Grid": ["IREDA.NS", "PFC.NS", "RECLTD.NS", "POWERGRID.NS", "BORORENEW.NS", "KPIGREEN.NS", "WAAREE.NS", "SJVN.NS", "GENSOL.NS", "SWSOLAR.NS"],
                },
                "Energy_Fossil": {
                    "Upstream_Integrated": ["RELIANCE.NS", "ONGC.NS", "OIL.NS", "GAIL.NS", "PETRONET.NS", "MRPL.NS", "GSPL.NS", "AEGISCHEM.NS", "GUJGASLTD.NS", "MGL.NS"],
                    "Downstream_Distribution": ["NTPC.NS", "COALINDIA.NS", "BPCL.NS", "IOC.NS", "HINDPETRO.NS", "CASTROLIND.NS", "IGL.NS", "NFL.NS", "RCF.NS", "CHAMBLFERT.NS"],
                },
                "Health": {
                    "Pharma_Generics": ["SUNPHARMA.NS", "CIPLA.NS", "DRREDDY.NS", "LUPIN.NS", "AUROPHARMA.NS", "ZYDUSLIFE.NS", "TORNTPHARM.NS", "ALKEM.NS", "IPCALAB.NS", "GLENMARK.NS"],
                    "Hospitals_Diagnostics": ["APOLLOHOSP.NS", "DIVISLAB.NS", "MANKIND.NS", "MAXHEALTH.NS", "GLAND.NS", "METROPOLIS.NS", "FORTIS.NS", "LALPATHLAB.NS", "KIMS.NS", "NH.NS"],
                },
                "Consumer_Tech_Beauty": {
                    "New_Age_Internet": ["ZOMATO.NS", "PAYTM.NS", "POLICYBZR.NS", "DELHIVERY.NS", "CARTRADE.NS", "MAPMYINDIA.NS", "NAUKRI.NS", "EASEMYTRIP.NS", "IXIGO.NS", "NYKAA.NS"],
                    "Beauty_D2C": ["HONASA.NS", "FSN.NS", "VEDL.NS", "EMAMILTD.NS", "GODREJCP.NS", "DABUR.NS", "MARICO.NS", "COLPAL.NS", "GILLETTE.NS", "BAJAJCON.NS"],
                },
                "Telecom_Media": {
                    "Telecom_Carriers": ["BHARTIARTL.NS", "IDEA.NS", "INDUSTOWER.NS", "TATACOMM.NS", "RAILTEL.NS", "HFCL.NS", "STLTECH.NS", "ITI.NS", "GTLINFRA.NS", "TEJASNET.NS"],
                    "Media_Entertainment": ["ZEEL.NS", "SUNTV.NS", "PVRINOX.NS", "NAZARA.NS", "SAREGAMA.NS", "TIPS.NS", "NETWORK18.NS", "DBCORP.NS", "JAGRAN.NS", "TV18BRDCST.NS"],
                },
                "Materials_Metals": {
                    "Steel_Mining": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "SAIL.NS", "NMDC.NS", "JINDALSTEL.NS", "HINDZINC.NS", "NATIONALUM.NS", "APLAPOLLO.NS"],
                    "Chemicals": ["PIDILITIND.NS", "SRF.NS", "UPL.NS", "AARTIIND.NS", "DEEPAKNTR.NS", "NAVINFLUOR.NS", "TATACHEM.NS", "GNFC.NS", "FLUOROCHEM.NS", "VINATIORGA.NS"],
                },
            },
        }

    # Fast "headline" universe for Overview / Strike List: top 20 large-cap US
    # (NASDAQ-heavy) + top 20 large-cap India (NSE) = 40 tickers total. Scored
    # in full on every "Run Full Audit" — small enough to stay fast. The full
    # 400-ticker sector/sub-sector universe above is only scored on-demand,
    # scoped to whichever sub-sector the user picks in the Analytics tab.
    HEADLINE_US = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "NFLX",
        "AMD", "ADBE", "PEP", "CSCO", "INTC", "QCOM", "TXN", "AMGN", "INTU", "PYPL",
    ]
    HEADLINE_IND = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "SBIN.NS",
        "BHARTIARTL.NS", "ITC.NS", "LT.NS", "HCLTECH.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS", "ASIANPAINT.NS",
        "WIPRO.NS", "ULTRACEMCO.NS", "NESTLEIND.NS",
    ]

    def get_headline_universe(self):
        """Returns {market: [tickers]} for the fast Overview/Strike List audit."""
        return {"US": self.HEADLINE_US, "IND": self.HEADLINE_IND}

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
            "industry": info.get('industry', 'N/A'),
        }

    def run_global_audit(self):
        for market, sectors in self.markets.items():
            print(f"[*] Auditing Market: {market}...")
            for sector, sub_sectors in sectors.items():
                for sub_sector, tickers in sub_sectors.items():
                    print(f"    - Sector: {sector} / {sub_sector}...")
                    sector_data = []
                    for t in tickers:
                        try:
                            data = self.fetch_metrics(t)
                            sector_data.append(data)
                            time.sleep(1)  # Rate limit protection
                        except Exception as e:
                            print(f"      [!] Warning: Failed on {t}: {e}")

                    df = pd.DataFrame(sector_data)
                    path = os.path.join(
                        self.base_dir, market, sector,
                        f"{market}_{sector}_{sub_sector}_vulnerability.csv"
                    )
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    df.to_csv(path, index=False)
                    print(f"    [+] {sector}/{sub_sector} Saved.")

    def run_headline_audit(self):
        """Fast path for Overview/Strike List: scores only the fixed 40-ticker
        headline universe (20 US + 20 India large caps), tagged with a
        dedicated "Headline" sector/sub-sector so it never mixes with the
        sector-drill-down raw files under data/raw/{market}/{sector}/."""
        for market, tickers in self.get_headline_universe().items():
            print(f"[*] Auditing Headline Market: {market}...")
            sector_data = []
            for t in tickers:
                try:
                    data = self.fetch_metrics(t)
                    sector_data.append(data)
                    time.sleep(1)  # Rate limit protection
                except Exception as e:
                    print(f"      [!] Warning: Failed on {t}: {e}")

            df = pd.DataFrame(sector_data)
            path = os.path.join(
                self.base_dir, market, "Headline",
                f"{market}_Headline_Large_Cap_vulnerability.csv"
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
            df.to_csv(path, index=False)
            print(f"    [+] Headline/{market} Saved.")

    def run_scoped_audit(self, market, sector, sub_sector):
        """On-demand path for the Analytics tab: fetches only the ~10 tickers
        in one sector/sub-sector, so a scenario run stays fast regardless of
        how large the full sector/sub-sector universe grows."""
        tickers = self.markets.get(market, {}).get(sector, {}).get(sub_sector, [])
        sector_data = []
        for t in tickers:
            try:
                data = self.fetch_metrics(t)
                sector_data.append(data)
                time.sleep(1)  # Rate limit protection
            except Exception as e:
                print(f"      [!] Warning: Failed on {t}: {e}")

        df = pd.DataFrame(sector_data)
        path = os.path.join(
            self.base_dir, market, sector,
            f"{market}_{sector}_{sub_sector}_vulnerability.csv"
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        return path

    def get_universe(self):
        """Returns the market -> sector -> sub_sector -> [tickers] map for UI drill-downs."""
        return self.markets


if __name__ == "__main__":
    collector = GlobalBilateralCollector()
    collector.run_global_audit()
