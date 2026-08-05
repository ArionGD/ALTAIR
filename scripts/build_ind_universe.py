"""
One-off screener: builds the IND-market sector/sub-sector ticker universe
for DataCollector.py — Energy/IT/Banking (2 categories each) plus
Automobiles (Two_Wheeler/Passenger/Commercial/HMV) and Defense
(Aeronautics/HMV/Drones), each populated with every candidate ticker whose
live market cap exceeds 10,000 crore.

NSE's own sector-index constituent API is currently blocked (bot-detection
returns a JS-challenge page instead of JSON — see NSEDataBridge.py), so this
uses yfinance for market cap instead. Candidate lists below are a broad,
manually-compiled set of NSE-listed companies per sub-sector (not a live
index feed) — run this script and review the output before trusting it as
exhaustive.

Run: python scripts/build_ind_universe.py
"""
import yfinance as yf

CRORE = 1e7
MIN_MARKET_CAP_CR = 10_000

# Broad candidate lists per sub-sector (NSE tickers). Not a guaranteed-
# complete official index constituent list - compiled from known public
# NSE listings in each category, then screened by live market cap below.
CANDIDATES = {
    "Energy": {
        "Upstream": [
            "ONGC.NS", "OIL.NS", "RELIANCE.NS", "VEDL.NS", "GAIL.NS",
            "PETRONET.NS", "MRPL.NS", "GSPL.NS", "AEGISCHEM.NS", "GUJGASLTD.NS",
            "OILCOUNTUB.NS", "SELAN.NS", "HINDOILEXP.NS",
        ],
        "Downstream": [
            "IOC.NS", "BPCL.NS", "HINDPETRO.NS", "NTPC.NS", "COALINDIA.NS",
            "CASTROLIND.NS", "IGL.NS", "MGL.NS", "NFL.NS", "RCF.NS",
            "CHAMBLFERT.NS", "GNFC.NS", "GSFC.NS", "GUJALKALI.NS",
            "TIDEWATER.NS", "ADANIGAS.NS",
        ],
    },
    "IT": {
        "Service": [
            # NOTE: LTIMindtree excluded - its yfinance symbol couldn't be
            # confirmed from here (LTIM.NS/LTIMINDTREE.NS/LTI.NS all 404'd).
            # It's a large company (likely well over 10,000cr) - verify the
            # correct symbol and add it back manually.
            "TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS",
            "TECHM.NS", "LTTS.NS", "OFSS.NS", "HEXT.NS", "MPHASIS.NS",
            "COFORGE.NS", "PERSISTENT.NS", "CYIENT.NS", "ZENSARTECH.NS",
            "SONATSOFTW.NS", "NEWGEN.NS", "INTELLECT.NS", "BSOFT.NS",
            "MASTEK.NS", "KPITTECH.NS", "TATAELXSI.NS", "FSL.NS",
        ],
        "Product": [
            "NAUKRI.NS", "ETERNAL.NS", "PAYTM.NS", "POLICYBZR.NS",
            "DELHIVERY.NS", "MAPMYINDIA.NS", "EASEMYTRIP.NS", "IXIGO.NS",
            "NYKAA.NS", "TANLA.NS", "ROUTE.NS", "HAPPSTMNDS.NS",
            "SAPPHIRE.NS", "AFFLE.NS", "NAZARA.NS", "RATEGAIN.NS",
        ],
    },
    "Banking": {
        "Bank": [
            "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS",
            "SBIN.NS", "INDUSINDBK.NS", "IDFCFIRSTB.NS", "FEDERALBNK.NS",
            "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS",
            "AUBANK.NS", "RBLBANK.NS", "BANDHANBNK.NS", "YESBANK.NS",
            "INDIANB.NS", "MAHABANK.NS", "IOB.NS", "CENTRALBK.NS",
            "UCOBANK.NS", "J&KBANK.NS", "KARURVYSYA.NS", "CUB.NS",
            "SOUTHBANK.NS",
        ],
        "NBFC": [
            "BAJFINANCE.NS", "BAJAJFINSV.NS", "LICHSGFIN.NS", "CHOLAFIN.NS",
            "RECLTD.NS", "PFC.NS", "MUTHOOTFIN.NS", "SHRIRAMFIN.NS",
            "SBICARD.NS", "MANAPPURAM.NS", "IREDA.NS", "PNBHOUSING.NS",
            "AAVAS.NS", "CREDITACC.NS", "POONAWALLA.NS", "IIFL.NS",
            "M&MFIN.NS", "SUNDARMFIN.NS", "ABCAPITAL.NS", "TATACAP.NS",
        ],
    },
    "Automobiles": {
        "Two_Wheeler": [
            "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "TVSMOTOR.NS", "EICHERMOT.NS",
            "TIINDIA.NS", "ATULAUTO.NS", "SUZUKI.NS",
        ],
        "Passenger": [
            # Tata Motors demerged Oct-Nov 2025: passenger vehicles + JLR
            # now trade separately as TMPV.NS (the old TATAMOTORS.NS ticker
            # no longer resolves - confirmed via direct yfinance lookup).
            "MARUTI.NS", "TMPV.NS", "M&M.NS", "FORCEMOT.NS",
        ],
        "Commercial": [
            "ASHOKLEY.NS", "BHARATFORG.NS", "MOTHERSON.NS", "BALKRISIND.NS",
            "EXIDEIND.NS", "SUNDRMFAST.NS", "BOSCHLTD.NS", "APOLLOTYRE.NS",
            "MRF.NS", "CEATLTD.NS", "JBM.NS", "ENDURANCE.NS", "SONACOMS.NS",
            "SCHAEFFLER.NS", "UNOMINDA.NS", "SANSERA.NS",
        ],
        "HMV": [
            # Heavy trucks/buses/heavy commercial vehicles specifically -
            # distinct from Commercial (light/mid CV + ancillaries) above.
            # TMCV.NS is Tata Motors' commercial-vehicle demerger (Nov 2025,
            # see Passenger's note above) - the natural HMV heavyweight.
            # VECV isn't separately listed on NSE (Volvo Eicher Commercial
            # Vehicles is an Eicher Motors subsidiary, not its own ticker).
            "ASHOKLEY.NS", "TMCV.NS", "SMLISUZU.NS",
        ],
    },
    "Defense": {
        "Aeronautics": [
            "HAL.NS", "BEL.NS", "BEML.NS", "DYNAMATECH.NS", "ASTRAMICRO.NS",
            "PARAS.NS", "MTARTECH.NS", "DATAPATTNS.NS",
        ],
        "HMV": [
            # Defense-specific heavy/armored vehicles - distinct ticker set
            # from Automobiles' HMV category above (different businesses,
            # BEML makes both civilian and defense heavy vehicles so it can
            # legitimately appear in both sectors' candidate lists).
            "BEML.NS", "TMCV.NS",
        ],
        "Drones": [
            # Pure-play drone manufacturers are mostly small-cap/unlisted in
            # India as of now - candidate list is intentionally short;
            # expect most/all to be screened OUT below 10,000cr, which is
            # a realistic reflection of the segment's current maturity, not
            # a screening error.
            "IDEAFORGE.NS", "ZENTEC.NS", "PARAS.NS",
        ],
    },
}


def screen():
    result = {}
    for sector, sub_sectors in CANDIDATES.items():
        result[sector] = {}
        for sub_sector, tickers in sub_sectors.items():
            kept = []
            for t in tickers:
                try:
                    info = yf.Ticker(t).info
                    mcap = info.get("marketCap") or 0
                    mcap_cr = mcap / CRORE
                    if mcap_cr > MIN_MARKET_CAP_CR:
                        kept.append(t)
                        print(f"[keep] {t:<15} {mcap_cr:>12,.0f} cr")
                    else:
                        print(f"[drop] {t:<15} {mcap_cr:>12,.0f} cr (below {MIN_MARKET_CAP_CR:,} cr)")
                except Exception as e:
                    print(f"[error] {t:<15} {e}")
            result[sector][sub_sector] = kept
    return result


if __name__ == "__main__":
    universe = screen()
    print("\n=== FINAL SCREENED UNIVERSE (>10,000 cr) ===")
    for sector, sub_sectors in universe.items():
        for sub_sector, tickers in sub_sectors.items():
            print(f'"{sub_sector}": {tickers!r},')
