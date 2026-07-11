"""
Builds the 40% enrichment tier: everything in GOLD_MASTER_30PCT.csv plus a
rolling cumulative Fed rate change — the "is the Fed in a hiking or
cutting cycle, and how aggressively" signal, distinct from the single-day
fed_funds_change already present.

Why this is a different signal from fed_funds_change
------------------------------------------------------
fed_funds_change (already in the 30% tier) is the DAY-OVER-DAY move —
almost always ~0 on any given day, since the Fed only actually moves rates
at ~8 FOMC meetings a year. A single day's change is mostly noise; it
can't tell you whether the Fed has been hiking steadily for the last
quarter or has been flat.

fed_funds_change_90d (added here) is the CUMULATIVE change over a
trailing 90-day window — total basis points moved, positive during a
hiking cycle, negative during a cutting cycle, near-zero during a hold.
This is the version of "the Fed is raising rates" that actually matches
how the effect plays out in practice: it's a sustained multi-month cycle,
not a single day's move, that changes gold's relative attractiveness
against a rising-yield alternative.

Column: fed_funds_change_90d = fed_funds_rate(t) - fed_funds_rate(t-90 calendar days)
(in percentage points, e.g. +1.25 = the rate is 1.25pp higher than 90 days ago)

Output: data/raw/Gold/GOLD_MASTER_40PCT.csv
Columns: (all of GOLD_MASTER_30PCT.csv) + fed_funds_change_90d
"""
import os
import pandas as pd

TIER_30PCT = os.path.join("data", "raw", "Gold", "GOLD_MASTER_30PCT.csv")
OUTPUT_FILE = os.path.join("data", "raw", "Gold", "GOLD_MASTER_40PCT.csv")

ROLLING_WINDOW_DAYS = 90


def build_gold_master_40pct():
    if not os.path.exists(TIER_30PCT):
        raise FileNotFoundError(f"{TIER_30PCT} not found — run build_gold_master_30pct.py first.")

    master = pd.read_csv(TIER_30PCT, parse_dates=["date"]).set_index("date")

    # Reindex to a continuous daily calendar so a 90-CALENDAR-day lookback
    # (not 90 trading rows) lands on the correct date even across
    # weekends/holidays, then forward-fill the rate across the gaps this
    # creates, and finally restore only the original trading-day rows.
    trading_days = master.index
    calendar_index = pd.date_range(trading_days.min(), trading_days.max(), freq="D")
    rate_daily = master["fed_funds_rate"].reindex(calendar_index).ffill()

    rate_90d_ago = rate_daily.reindex(rate_daily.index - pd.Timedelta(days=ROLLING_WINDOW_DAYS)).values
    change_90d = pd.Series(rate_daily.values - rate_90d_ago, index=rate_daily.index)

    master["fed_funds_change_90d"] = change_90d.reindex(trading_days)
    master = master.dropna(subset=["fed_funds_change_90d"])

    master = master.reset_index()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    master.to_csv(OUTPUT_FILE, index=False)

    print(f"\n[+] Gold Master 40% tier written: {OUTPUT_FILE}")
    print(f"    Rows: {len(master)}  |  Date range: {master['date'].min()} to {master['date'].max()}")
    print(master[["date", "fed_funds_rate", "fed_funds_change_90d"]].head())
    print("...")
    print(master[["date", "fed_funds_rate", "fed_funds_change_90d"]].tail())

    # Sanity check: correlate gold_return against the cumulative 90d rate
    # move — expect a cleaner, more negative relationship than the noisy
    # single-day rate change would show, since a sustained hiking cycle is
    # the version of "the Fed hurts gold" that actually holds.
    fed_funds_change_1d = master["fed_funds_rate"].diff()
    corr_90d = master["gold_return"].corr(master["fed_funds_change_90d"])
    corr_1d = master["gold_return"].corr(fed_funds_change_1d)
    print(f"\n[*] Correlation check: gold_return vs fed_funds_change_90d (cumulative) = {corr_90d:.3f}")
    print(f"[*] Correlation check: gold_return vs fed_funds_change (single-day)       = {corr_1d:.3f}")
    print("    (Expect the 90-day cumulative version to show a cleaner, more negative")
    print("     relationship than the noisy single-day change.)")

    return OUTPUT_FILE


if __name__ == "__main__":
    build_gold_master_40pct()
