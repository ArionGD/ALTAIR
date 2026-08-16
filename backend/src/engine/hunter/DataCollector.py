import pandas as pd
import os
import time
from datetime import datetime
from src.engine.hunter.SovereignAuditor import SovereignAuditor

class GlobalBilateralCollector:
    """
    ALTAIR Universe Collector.
    Fixed universe: market -> sector -> sub_sector -> tickers.
    US market: 10 sectors x 2 sub-sectors x 10 tickers = 200 tickers.
    IND market: 5 sectors (Energy: Upstream/Downstream, IT: Service/Product,
    Banking: Bank/NBFC, Automobiles: Two_Wheeler/Passenger/Commercial/HMV,
    Defense: Aeronautics/HMV/Drones), each sub-sector holding every screened
    NSE ticker with live market cap > 10,000 crore (variable count per
    sub-sector, not a fixed 10 - see scripts/build_ind_universe.py). Note
    "HMV" appears under both Automobiles and Defense as distinct categories
    with mostly-distinct ticker sets (BEML/TMCV legitimately appear in both,
    being dual-use civilian/defense heavy-vehicle makers).
    Sub-sectors let scenario exposure (e.g. oil-shock beta) vary within a
    sector instead of being one flat sector-wide number.
    """
    def __init__(self, base_dir="../database/raw"):
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
            # IND universe: 3 sectors x 2 sub-sectors, each populated by
            # screening a broad candidate list for live market cap > 10,000
            # crore (see scripts/build_ind_universe.py, run against yfinance
            # since NSE's own sector-index API is currently bot-blocked -
            # see NSEDataBridge.py). Re-run that script and paste fresh
            # results here if this universe needs updating later; LTIMindtree
            # is deliberately absent from IT/Service - its correct yfinance
            # symbol couldn't be confirmed, see the script's inline note.
            "IND": {
                "Energy": {
                    "Upstream": ["ONGC.NS", "OIL.NS", "RELIANCE.NS", "VEDL.NS", "GAIL.NS", "PETRONET.NS", "MRPL.NS", "GSPL.NS", "GUJGASLTD.NS"],
                    "Downstream": ["IOC.NS", "BPCL.NS", "HINDPETRO.NS", "NTPC.NS", "COALINDIA.NS", "CASTROLIND.NS", "IGL.NS", "MGL.NS", "CHAMBLFERT.NS"],
                },
                "IT": {
                    "Service": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS", "LTTS.NS", "OFSS.NS", "HEXT.NS", "MPHASIS.NS", "COFORGE.NS", "PERSISTENT.NS", "ZENSARTECH.NS", "INTELLECT.NS", "KPITTECH.NS", "TATAELXSI.NS", "FSL.NS"],
                    "Product": ["NAUKRI.NS", "ETERNAL.NS", "PAYTM.NS", "POLICYBZR.NS", "DELHIVERY.NS", "NYKAA.NS", "AFFLE.NS", "NAZARA.NS", "RATEGAIN.NS"],
                },
                "Banking": {
                    "Bank": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS", "INDUSINDBK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS", "AUBANK.NS", "RBLBANK.NS", "BANDHANBNK.NS", "YESBANK.NS", "INDIANB.NS", "MAHABANK.NS", "IOB.NS", "CENTRALBK.NS", "UCOBANK.NS", "J&KBANK.NS", "KARURVYSYA.NS", "CUB.NS", "SOUTHBANK.NS"],
                    "NBFC": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "LICHSGFIN.NS", "CHOLAFIN.NS", "RECLTD.NS", "PFC.NS", "MUTHOOTFIN.NS", "SHRIRAMFIN.NS", "SBICARD.NS", "MANAPPURAM.NS", "IREDA.NS", "PNBHOUSING.NS", "AAVAS.NS", "CREDITACC.NS", "POONAWALLA.NS", "IIFL.NS", "M&MFIN.NS", "SUNDARMFIN.NS", "ABCAPITAL.NS", "TATACAP.NS"],
                },
                "Automobiles": {
                    "Two_Wheeler": ["HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "TVSMOTOR.NS", "EICHERMOT.NS", "TIINDIA.NS"],
                    "Passenger": ["MARUTI.NS", "TMPV.NS", "M&M.NS", "FORCEMOT.NS"],
                    "Commercial": ["ASHOKLEY.NS", "BHARATFORG.NS", "MOTHERSON.NS", "BALKRISIND.NS", "EXIDEIND.NS", "SUNDRMFAST.NS", "BOSCHLTD.NS", "APOLLOTYRE.NS", "MRF.NS", "CEATLTD.NS", "ENDURANCE.NS", "SONACOMS.NS", "SCHAEFFLER.NS", "UNOMINDA.NS", "SANSERA.NS", "TMCV.NS"],
                    "HMV": [],
                },
                "Defense": {
                    "Aeronautics": ["HAL.NS", "BEL.NS", "ASTRAMICRO.NS", "PARAS.NS", "MTARTECH.NS", "DATAPATTNS.NS"],
                    "HMV": ["BEML.NS"],
                    "Drones": ["ZENTEC.NS"],
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

    def resolve_filtered_tickers(self, market, sector=None, sub_sector=None, ticker=None):
        """Resolves a market/sector/sub_sector/ticker filter (any of the last
        three may be None/omitted, meaning "all") into a flat list of
        (ticker, sector, sub_sector) tuples, tagged with their sector/
        sub_sector so the result can be scored and grouped without a
        separate CSV-tagging pass. Used by the Sector Ranker tool, which
        (unlike the oil-shock scenario tool) may span every sub-sector in a
        sector or every sector in a market, not just one fixed ~10-ticker
        sub-sector."""
        sectors = self.markets.get(market, {})
        if sector:
            sectors = {sector: sectors.get(sector, {})}

        resolved = []
        for sec, sub_sectors in sectors.items():
            chosen = {sub_sector: sub_sectors.get(sub_sector, [])} if sub_sector else sub_sectors
            for sub, tickers in chosen.items():
                for t in tickers:
                    if ticker and t != ticker:
                        continue
                    resolved.append((t, sec, sub))
        return resolved

    def fetch_filtered(self, market, sector=None, sub_sector=None, ticker=None):
        """On-demand fetch for the Sector Ranker tool: resolves the filter to
        a ticker list (see resolve_filtered_tickers) and fetches each live,
        tagging rows with market/sector/sub_sector directly - no CSV
        round-trip, since results are scored and returned in the same
        request rather than cached to data/raw/ like the fixed-universe
        audits above."""
        targets = self.resolve_filtered_tickers(market, sector, sub_sector, ticker)
        rows = []
        for t, sec, sub in targets:
            try:
                data = self.fetch_metrics(t)
                data['market'] = market
                data['sector'] = sec
                data['sub_sector'] = sub
                rows.append(data)
                time.sleep(1)  # Rate limit protection
            except Exception as e:
                print(f"      [!] Warning: Failed on {t}: {e}")
        return pd.DataFrame(rows)


if __name__ == "__main__":
    collector = GlobalBilateralCollector()
    collector.run_global_audit()
