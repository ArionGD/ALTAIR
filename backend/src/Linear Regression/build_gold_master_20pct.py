"""
Builds the 20% enrichment tier of the Gold Master sheet: everything in
GOLD_MASTER_10PCT.csv (gold, oil, Fed funds rate) plus a proper
inflation-adjustment column.

Inflation math
--------------
US CPI (inflation) is published MONTHLY by the BLS, not daily or yearly —
the "annual inflation rate" itself is a derived trailing 12-month % change
in the CPI index. To use it against gold's daily returns, the annual rate
has to be converted into a daily-equivalent rate that COMPOUNDS back to
the real annual figure over a year:

    daily_rate = (1 + annual_rate) ** (1/252) - 1

(252 = standard trading-day count in a year.) This is different from,
and more correct than, naive division (annual_rate / 252) — naive
division under-compounds and drifts increasingly wrong over the year;
the exponential form is exact by construction.

Each day's "real" (inflation-adjusted) gold return is then:

    real_gold_return = gold_return - inflation_daily_rate

Example matching the user's framing: if gold rises 5% over a year while
inflation runs 4% over the same year, the true (real) purchasing-power
gain is not simply 5% - 4% = 1% for every day equally — but summed/
compounded over the whole year, a 5% nominal gain against 4% inflation
does work out to roughly a 1% real gain. Spreading each side into a
correctly-compounding daily rate is what makes that hold at the daily
granularity this sheet operates at.

Output: data/raw/Gold/GOLD_MASTER_20PCT.csv
Columns: (all of GOLD_MASTER_10PCT.csv) + inflation_annual_rate,
         inflation_daily_rate, real_gold_return
"""
import os
import pandas as pd
import pandas_datareader.data as web

TIER_10PCT = os.path.join("data", "raw", "Gold", "GOLD_MASTER_10PCT.csv")
OUTPUT_FILE = os.path.join("data", "raw", "Gold", "GOLD_MASTER_20PCT.csv")

CPI_SERIES = "CPIAUCSL"  # CPI for All Urban Consumers, US city average, monthly
TRADING_DAYS_PER_YEAR = 252


def fetch_annual_inflation_rate():
    """Returns a daily-indexed Series of the trailing 12-month CPI inflation
    rate, forward-filled from the monthly CPI print to every calendar day."""
    print(f"[*] Fetching CPI (FRED: {CPI_SERIES})...")
    start = pd.Timestamp.now() - pd.DateOffset(years=11)  # +1yr buffer for the pct_change(12) window
    cpi = web.DataReader(CPI_SERIES, "fred", start=start)[CPI_SERIES]

    # BLS occasionally has a gap month (e.g. government shutdown delays) —
    # forward-fill within the monthly series itself before computing the
    # trailing rate, so one missing print doesn't create a spurious spike.
    cpi = cpi.ffill()

    annual_rate = cpi.pct_change(periods=12)  # trailing 12-month % change
    annual_rate = annual_rate.dropna()

    # Reindex from monthly to daily, forward-filling — a CPI print released
    # for e.g. June stays "the current known annual rate" every day until
    # July's print arrives.
    daily_index = pd.date_range(annual_rate.index.min(), pd.Timestamp.now(), freq="D")
    daily_rate = annual_rate.reindex(daily_index, method="ffill")
    daily_rate.index.name = "date"
    return daily_rate.rename("inflation_annual_rate")


def build_gold_master_20pct():
    if not os.path.exists(TIER_10PCT):
        raise FileNotFoundError(f"{TIER_10PCT} not found — run build_gold_master.py first.")

    base = pd.read_csv(TIER_10PCT, parse_dates=["date"]).set_index("date")
    inflation_annual = fetch_annual_inflation_rate()

    master = base.join(inflation_annual, how="left")
    master["inflation_annual_rate"] = master["inflation_annual_rate"].ffill()
    master = master.dropna(subset=["inflation_annual_rate"])

    # Exact daily-compounding conversion — see module docstring.
    master["inflation_daily_rate"] = (1 + master["inflation_annual_rate"]) ** (1 / TRADING_DAYS_PER_YEAR) - 1

    master["real_gold_return"] = master["gold_return"] - master["inflation_daily_rate"]

    master = master.reset_index()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    master.to_csv(OUTPUT_FILE, index=False)

    print(f"\n[+] Gold Master 20% tier written: {OUTPUT_FILE}")
    print(f"    Rows: {len(master)}  |  Date range: {master['date'].min()} to {master['date'].max()}")
    print(master[["date", "gold_return", "inflation_annual_rate", "inflation_daily_rate", "real_gold_return"]].head())
    print("...")
    print(master[["date", "gold_return", "inflation_annual_rate", "inflation_daily_rate", "real_gold_return"]].tail())

    # Sanity check matching the user's framing: sum of nominal vs real
    # returns over the full window, roughly comparable to "5% nominal - 4%
    # inflation ~= 1% real" at the annual level.
    total_nominal = (1 + master["gold_return"]).prod() - 1
    total_real = (1 + master["real_gold_return"]).prod() - 1
    print(f"\n[*] Over the full window: nominal gold return = {total_nominal:.2%}, "
          f"inflation-adjusted (real) return = {total_real:.2%}")

    return OUTPUT_FILE


if __name__ == "__main__":
    build_gold_master_20pct()
