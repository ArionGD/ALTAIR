"""
Builds the 30% enrichment tier of the Gold Master sheet: everything in
GOLD_MASTER_20PCT.csv (gold, oil, Fed funds rate, inflation) plus:

  - real_10y_yield: the 10-Year TIPS yield (FRED DFII10) — gold pays no
    interest, so its opportunity cost is the REAL (inflation-adjusted)
    yield on a safe asset. This is widely considered gold's single
    strongest explanatory factor — stronger than nominal rates or
    inflation alone, because it nets both together into what actually
    matters to a gold holder: "what am I giving up by holding gold
    instead of a real-yielding safe asset."

  - dollar_index: trade-weighted US Dollar Index (FRED DTWEXBGS). Gold is
    priced in USD globally, so a stronger dollar mechanically makes gold
    more expensive for the rest of the world, dampening demand — the
    classic inverse dollar/gold relationship.

Both are added as daily levels AND daily % changes (returns), since the
EGB model works on returns for the same reason gold_return/oil_return are
returns, not raw levels — see build_gold_master.py's docstring for why
raw levels create spurious "correlation" from shared long-term trends.

Output: data/raw/Gold/GOLD_MASTER_30PCT.csv
Columns: (all of GOLD_MASTER_20PCT.csv) + real_10y_yield, real_10y_yield_change,
         dollar_index, dollar_index_return
"""
import os
import pandas as pd
import pandas_datareader.data as web

TIER_20PCT = os.path.join("data", "raw", "Gold", "GOLD_MASTER_20PCT.csv")
OUTPUT_FILE = os.path.join("data", "raw", "Gold", "GOLD_MASTER_30PCT.csv")

REAL_YIELD_SERIES = "DFII10"   # 10-Year Treasury Inflation-Indexed Security, constant maturity
DOLLAR_INDEX_SERIES = "DTWEXBGS"  # Trade Weighted US Dollar Index: Broad, Goods and Services


def fetch_fred_series(series_id, label):
    print(f"[*] Fetching {label} (FRED: {series_id})...")
    start = pd.Timestamp.now() - pd.DateOffset(years=11)
    df = web.DataReader(series_id, "fred", start=start)[series_id]
    df.index.name = "date"
    return df.rename(label)


def build_gold_master_30pct():
    if not os.path.exists(TIER_20PCT):
        raise FileNotFoundError(f"{TIER_20PCT} not found — run build_gold_master_20pct.py first.")

    base = pd.read_csv(TIER_20PCT, parse_dates=["date"]).set_index("date")

    real_yield = fetch_fred_series(REAL_YIELD_SERIES, "real_10y_yield")
    dollar_index = fetch_fred_series(DOLLAR_INDEX_SERIES, "dollar_index")

    master = base.join(real_yield, how="left").join(dollar_index, how="left")

    # Both FRED series only publish on business days and have occasional
    # gaps (holidays, data revisions) — forward-fill so every gold trading
    # day still has the last known value, same approach as the Fed funds
    # rate and CPI joins in the earlier tiers.
    master["real_10y_yield"] = master["real_10y_yield"].ffill()
    master["dollar_index"] = master["dollar_index"].ffill()
    master = master.dropna(subset=["real_10y_yield", "dollar_index"])

    # Real yield is a rate already (in percentage points), so its day-over-
    # day CHANGE (not a % return) is the meaningful feature — a move from
    # 2.0% to 2.1% is a 0.1 percentage-point change, not "5% growth".
    master["real_10y_yield_change"] = master["real_10y_yield"].diff()

    # Dollar index is a price-like level, so % return is the right
    # transform — same reasoning as gold_return/oil_return.
    master["dollar_index_return"] = master["dollar_index"].pct_change()

    master = master.dropna(subset=["real_10y_yield_change", "dollar_index_return"])
    master = master.reset_index()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    master.to_csv(OUTPUT_FILE, index=False)

    print(f"\n[+] Gold Master 30% tier written: {OUTPUT_FILE}")
    print(f"    Rows: {len(master)}  |  Date range: {master['date'].min()} to {master['date'].max()}")
    print(master[["date", "gold_return", "real_10y_yield", "real_10y_yield_change",
                   "dollar_index", "dollar_index_return"]].head())
    print("...")
    print(master[["date", "gold_return", "real_10y_yield", "real_10y_yield_change",
                   "dollar_index", "dollar_index_return"]].tail())

    # Quick directional sanity check: gold vs real yield should be
    # negatively correlated (higher real yield -> less attractive to hold
    # non-yielding gold), gold vs dollar should also be negatively
    # correlated (stronger dollar -> gold more expensive elsewhere).
    corr_yield = master["gold_return"].corr(master["real_10y_yield_change"])
    corr_dollar = master["gold_return"].corr(master["dollar_index_return"])
    print(f"\n[*] Correlation check: gold_return vs real_10y_yield_change = {corr_yield:.3f} (expect negative)")
    print(f"[*] Correlation check: gold_return vs dollar_index_return   = {corr_dollar:.3f} (expect negative)")

    return OUTPUT_FILE


if __name__ == "__main__":
    build_gold_master_30pct()
