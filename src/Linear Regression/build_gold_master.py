"""
Builds the Gold Master enriched CSV: one row per trading day, with gold
price, oil price, and the Fed funds rate aligned on the same date.

This is the first, 3-factor enrichment pass (10% of a fuller multi-factor
sheet) — a deliberately small starting point to validate the pipeline and
get a first look at what `Patterns EGB` finds before adding more factors.

Output: data/raw/Gold/GOLD_MASTER.csv
Columns: date, gold_close, gold_return, oil_close, oil_return, fed_funds_rate
"""
import os
import pandas as pd
import yfinance as yf
import pandas_datareader.data as web

OUTPUT_DIR = os.path.join("data", "raw", "Gold")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "GOLD_MASTER.csv")

LOOKBACK = "10y"
GOLD_TICKER = "GC=F"   # Gold futures (continuous)
OIL_TICKER = "CL=F"    # WTI crude futures (continuous)
FRED_SERIES = "DFF"    # Effective Federal Funds Rate (daily)


def fetch_price_series(ticker, label):
    print(f"[*] Fetching {label} ({ticker})...")
    hist = yf.Ticker(ticker).history(period=LOOKBACK, interval="1d")
    if hist.empty:
        raise RuntimeError(f"No data returned for {ticker}")
    hist.index = hist.index.tz_localize(None)
    close = hist["Close"].rename(f"{label}_close")
    close.index.name = "date"
    return close


def fetch_fed_funds_rate():
    print(f"[*] Fetching Fed Funds Rate (FRED: {FRED_SERIES})...")
    start = pd.Timestamp.now() - pd.DateOffset(years=10)
    df = web.DataReader(FRED_SERIES, "fred", start=start)
    df.index.name = "date"
    return df[FRED_SERIES].rename("fed_funds_rate")


def build_gold_master():
    gold = fetch_price_series(GOLD_TICKER, "gold")
    oil = fetch_price_series(OIL_TICKER, "oil")
    fed = fetch_fed_funds_rate()

    # Fed Funds Rate is a daily series but doesn't trade on weekends/holidays
    # the same way futures do — align everything to the intersection of
    # trading days present in the price series, then forward-fill the rate
    # (a rate published Friday is still "in effect" through the weekend).
    master = pd.concat([gold, oil], axis=1, join="inner")
    master = master.join(fed, how="left")
    master["fed_funds_rate"] = master["fed_funds_rate"].ffill()

    master = master.dropna(subset=["gold_close", "oil_close", "fed_funds_rate"])

    master["gold_return"] = master["gold_close"].pct_change()
    master["oil_return"] = master["oil_close"].pct_change()
    master = master.dropna(subset=["gold_return", "oil_return"])

    master = master[[
        "gold_close", "gold_return", "oil_close", "oil_return", "fed_funds_rate"
    ]]
    master = master.reset_index()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    master.to_csv(OUTPUT_FILE, index=False)

    print(f"\n[+] Gold Master sheet written: {OUTPUT_FILE}")
    print(f"    Rows: {len(master)}  |  Date range: {master['date'].min()} to {master['date'].max()}")
    print(master.head())
    print("...")
    print(master.tail())
    return OUTPUT_FILE


if __name__ == "__main__":
    build_gold_master()
