"""Lexicon-based sentiment scoring for scraped search/social snippets.

Deliberately simple (word-list counting, no ML model) to match the
prototyping phase of this project. Swap in a real classifier later if the
signal proves useful.
"""

BULLISH_WORDS = [
    "buy", "bullish", "rally", "surge", "soar", "breakout", "upgrade",
    "outperform", "beat estimates", "record high", "strong buy",
    "undervalued", "momentum", "uptrend", "gains", "rocket", "accumulate",
    "oversold bounce", "buy the dip", "multibagger",
]

BEARISH_WORDS = [
    "sell", "bearish", "crash", "plunge", "slump", "downgrade",
    "underperform", "miss estimates", "record low", "strong sell",
    "overvalued", "bubble", "downtrend", "losses", "dump", "short",
    "fraud", "bankruptcy", "default", "scam", "delisted", "insolvency",
]


def score_text(text: str) -> float:
    """Returns a score in [-1, 1]: (bullish hits - bearish hits) / total hits.

    Returns 0.0 for neutral or no-signal text.
    """
    lowered = text.lower()
    bull_hits = sum(lowered.count(word) for word in BULLISH_WORDS)
    bear_hits = sum(lowered.count(word) for word in BEARISH_WORDS)
    total = bull_hits + bear_hits
    if total == 0:
        return 0.0
    return round((bull_hits - bear_hits) / total, 3)
