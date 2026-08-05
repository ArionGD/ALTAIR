"""
ALTAIR: Swing-Trading Scanner (two-sided long/short).

Combines the existing fundamental engine (VulnerabilityRanker's
astra_strike_score - 0..100, higher = more fragile) with TechnicalScore's
momentum score (-100..100, positive = bullish) into a swing-trade verdict:

  LONG SETUP  - fundamentally STRONG (low astra_strike_score) AND
                technically bullish (positive, above-threshold technical_score)
  SHORT SETUP - fundamentally WEAK (high astra_strike_score) AND
                technically bearish (negative, below-threshold technical_score)
  NO SETUP    - everything else: strong fundamentals with bearish technicals,
                weak fundamentals with bullish technicals, or technicals too
                flat/mixed to act on either direction.

Fundamentals GATE eligibility rather than blending into one number - swing
trading a fragile balance sheet on a lucky bullish chart, or shorting a
genuinely strong company on a temporary dip, is exactly the mismatched-signal
case this scanner is meant to screen OUT, not average away.
"""
from src.engine.swing.TechnicalScore import calculate_technical_score

# astra_strike_score thresholds (0-100 fragility scale, same scale
# VulnerabilityRanker/Sector Ranker already use for STRONG/STABLE/CAUTION/WEAK).
FUNDAMENTAL_STRONG_MAX = 40.0   # <= this is eligible for the LONG side
FUNDAMENTAL_WEAK_MIN = 60.0     # >= this is eligible for the SHORT side

# technical_score thresholds (-100..100 scale from TechnicalScore).
TECHNICAL_BULLISH_MIN = 20.0    # >= this counts as a real bullish setup
TECHNICAL_BEARISH_MAX = -20.0   # <= this counts as a real bearish setup


def classify_swing_setup(astra_strike_score, technical_score):
    """Pure classification logic, split out from the per-ticker fetch/score
    below so it's independently testable against fixed inputs."""
    is_fundamentally_strong = astra_strike_score is not None and astra_strike_score <= FUNDAMENTAL_STRONG_MAX
    is_fundamentally_weak = astra_strike_score is not None and astra_strike_score >= FUNDAMENTAL_WEAK_MIN
    is_technically_bullish = technical_score >= TECHNICAL_BULLISH_MIN
    is_technically_bearish = technical_score <= TECHNICAL_BEARISH_MAX

    if is_fundamentally_strong and is_technically_bullish:
        return "LONG SETUP"
    if is_fundamentally_weak and is_technically_bearish:
        return "SHORT SETUP"
    return "NO SETUP"


def scan_ticker(row, auditor, ranker):
    """Scores one already-fundamentally-scored row (must have ticker/sector/
    pe_ratio, same shape VulnerabilityRanker.score_dataframe rows have) with
    the technical layer, and classifies the combined swing verdict."""
    ticker = row['ticker']

    fundamental_result = ranker.calculate_avs_score_v11(row)
    technical_result = calculate_technical_score(ticker, auditor)

    verdict = classify_swing_setup(
        fundamental_result['astra_strike_score'],
        technical_result['technical_score'],
    )

    return {
        'ticker': ticker,
        'market': row.get('market'),
        'sector': row.get('sector'),
        'sub_sector': row.get('sub_sector'),
        'astra_strike_score': fundamental_result['astra_strike_score'],
        **{k: v for k, v in technical_result.items()},
        'swing_verdict': verdict,
    }


def rank_swing_results(results):
    """Sorts a list of scan_ticker-shaped dicts (each with swing_verdict/
    technical_score) and assigns 'rank': LONG SETUP first (strongest
    technical_score first), then SHORT SETUP (most bearish technical_score
    first), then NO SETUP - so the two actionable extremes surface before
    the noise. Mutates and returns the same list. Shared by scan_dataframe
    below and by /api/v1/swing/scan's per-ticker-cached path in
    ScenarioRoutes.py, which can't use scan_dataframe directly since it
    needs to check the cache per-ticker before deciding whether to compute."""
    verdict_order = {"LONG SETUP": 0, "SHORT SETUP": 1, "NO SETUP": 2}

    def sort_key(r):
        verdict_rank = verdict_order.get(r['swing_verdict'], 3)
        # Within LONG: highest technical_score first. Within SHORT: lowest
        # (most negative) first. Both expressed as "more negative = earlier"
        # so a single ascending sort handles both directions.
        tie_break = -r['technical_score'] if r['swing_verdict'] == "LONG SETUP" else r['technical_score']
        return (verdict_rank, tie_break)

    results.sort(key=sort_key)
    for i, r in enumerate(results, start=1):
        r['rank'] = i
    return results


def scan_dataframe(tagged_df, auditor, ranker):
    """Runs scan_ticker over every row of an already market/sector/sub_sector-
    tagged dataframe (same shape DataCollector.fetch_filtered produces), and
    returns results ranked via rank_swing_results."""
    results = [scan_ticker(row, auditor, ranker) for _, row in tagged_df.iterrows()]
    return rank_swing_results(results)
