BAILOUT_MAP = {
    # IND Market: High Protection (PSUs / BFSI)
    "SBIN.NS": 100, "ONGC.NS": 100, "NTPC.NS": 100, "TCS.NS": 90, "INFY.NS": 85,
    "HDFCBANK.NS": 80, "ICICIBANK.NS": 80, "LT.NS": 80, "RELIANCE.NS": 80,

    # IND Market: The Sacrifices (Consumer Tech / Beauty)
    "ZOMATO.NS": 0, "PAYTM.NS": 0, "NYKAA.NS": 5, "HONASA.NS": 0, "DELHIVERY.NS": 5,
    "POLICYBZR.NS": 5, "CARTRADE.NS": 10,

    # US Market (Sovereign Floor)
    "INTC": 100, "BA": 100, "LMT": 100, "RTX": 100, "JPM": 100, "AAPL": 100,
    "TSLA": 15, "AMT": 10, "F": 20, "GM": 20, "ABNB": 15, "UBER": 15, "DASH": 10,
    "PATH": 5, "SNOW": 5, "PLTR": 20, "EL": 25, "ULTA": 20,
}

DEFAULT_BAILOUT_PROBABILITY = 30


def get_bailout_probability(ticker_symbol):
    return BAILOUT_MAP.get(ticker_symbol, DEFAULT_BAILOUT_PROBABILITY)
