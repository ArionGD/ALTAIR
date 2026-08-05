"""
ALTAIR: Swing-Trading Technical Momentum Engine.

Computes a -100..+100 momentum score from daily OHLCV history (yfinance
`.history()`, free, no extra data source) - positive means bullish
technical setup, negative means bearish. This is deliberately swing-horizon
(days to weeks), not intraday: yfinance's intraday bars are thin/unreliable
(only ~7 days of 1-minute history, rate-limited in practice), but its daily
history is solid (250+ trading days reliably available), which is exactly
enough for a 200-day moving average - the coarsest, most swing-relevant
trend signal.

This is timing/entry signal only - it says nothing about whether a company
is fundamentally sound. Pairs with VulnerabilityRanker's astra_strike_score
(fundamental strength/fragility) in SwingScanner.py, which gates eligibility
before this module's score decides direction/timing.
"""
import pandas as pd


def _rsi(closes, period=14):
    """Standard Wilder RSI. Returns the latest value, or None if there
    isn't enough history yet (needs period+1 closes minimum)."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    latest = rsi.iloc[-1]
    return None if pd.isna(latest) else float(latest)


def _up_down_volume_ratio(closes, volumes, lookback=20):
    """
    Up/Down Volume Ratio, expressed as a signed percentage: over the last
    `lookback` trading days, sum volume on days the stock closed higher than
    the prior day ("up days") vs. days it closed lower ("down days"), then
    return (up_volume - down_volume) / (up_volume + down_volume) * 100.

    This is a disclosed PROXY for buy/sell pressure, not true order-flow
    (buyer-initiated vs. seller-initiated trades) - yfinance has no tick/
    bid-ask data to compute the real thing (confirmed: its Ticker object
    exposes only OHLCV bars, nothing trade-level), and genuine order-flow
    needs a live broker feed (e.g. Kite Connect), a separate, bigger
    integration. Positive = more volume concentrated on up-days (buying
    pressure proxy); negative = more volume on down-days (selling pressure
    proxy). Same "real data, honestly labeled as a substitute" approach as
    BankScore.py's ROA/ROE proxy for NPA/CASA.
    """
    if len(closes) < lookback + 1:
        return None

    deltas = closes.diff()
    up_days = deltas > 0
    down_days = deltas < 0

    up_volume = volumes[up_days].tail(lookback).sum()
    down_volume = volumes[down_days].tail(lookback).sum()
    total_volume = up_volume + down_volume

    if total_volume <= 0:
        return None

    return float((up_volume - down_volume) / total_volume * 100)


def calculate_technical_score(ticker_symbol, auditor, history_period="1y"):
    """
    Technical Momentum Score (-100..+100, positive = bullish, negative =
    bearish), from 3 factors:
      1. Trend regime (40%) - price vs 50-day and 200-day moving averages.
         Price above both + 50MA above 200MA ("golden cross" regime) is the
         strongest bullish trend signal; the mirror image is the strongest
         bearish one.
      2. Momentum direction (35%) - RSI(14), read as directional momentum
         rather than a pure overbought/oversold flag: RSI trending toward
         70+ is strengthening bullish momentum, toward 30- is strengthening
         bearish momentum. (RSI > 80 or < 20 gets dampened slightly - a
         swing entry chasing an already-extreme move is lower quality, not
         higher.)
      3. Volume confirmation (25%) - latest volume vs its 20-day average.
         A price move on below-average volume is a weaker, less trustworthy
         signal than the same move on above-average volume; this factor
         scales the other two rather than standing alone (a huge-volume
         move with no price trend isn't a signal by itself).
    """
    ticker = auditor.get_ticker_object(ticker_symbol)
    hist = ticker.history(period=history_period)

    if hist.empty or len(hist) < 60:
        # Not enough history for a meaningful 50-day trend read (200-day
        # trend degrades gracefully to a neutral contribution below) -
        # newly-listed tickers mostly hit this path.
        return {
            "price": None, "ma50": None, "ma200": None, "rsi14": None,
            "volume_ratio": None, "buy_sell_ratio": None, "technical_score": 0.0,
        }

    closes = hist['Close']
    volumes = hist['Volume']
    price = float(closes.iloc[-1])

    ma50 = float(closes.rolling(50).mean().iloc[-1])
    ma200_series = closes.rolling(200).mean()
    ma200 = float(ma200_series.iloc[-1]) if not pd.isna(ma200_series.iloc[-1]) else None

    # 1. Trend regime (40%): each condition below contributes independently
    # so a ticker with only 60-199 days of history (no valid 200MA yet)
    # still gets a real trend score from the 50MA/price relationship alone,
    # rather than the whole factor collapsing to neutral.
    trend_signal = 0.0
    trend_weight = 0.0
    trend_signal += 50.0 if price > ma50 else -50.0
    trend_weight += 50.0
    if ma200 is not None:
        trend_signal += 30.0 if price > ma200 else -30.0
        trend_signal += 20.0 if ma50 > ma200 else -20.0
        trend_weight += 50.0
    trend_score = (trend_signal / trend_weight) * 100  # normalize to -100..100

    # 2. Momentum direction (35%): map RSI's 0-100 scale to a -100..100
    # directional score centered on 50 (neutral), with high/low extremes
    # (>80 or <20) pulled back slightly - chasing an already-extreme move
    # is a lower-quality swing entry, not a stronger one.
    rsi14 = _rsi(closes)
    if rsi14 is None:
        momentum_score = 0.0
    else:
        momentum_score = (rsi14 - 50) * 2  # -100..100
        if rsi14 > 80 or rsi14 < 20:
            momentum_score *= 0.7

    # 3. Volume confirmation (25%): scales the combined trend+momentum
    # signal - a move on thin volume is discounted, one on heavy volume is
    # trusted at full strength. Ratio is capped so one freak volume spike
    # doesn't dominate the score.
    avg_volume_20 = volumes.rolling(20).mean().iloc[-1]
    latest_volume = volumes.iloc[-1]
    if pd.isna(avg_volume_20) or avg_volume_20 <= 0:
        volume_ratio = None
        volume_confidence = 0.75  # neutral-ish confidence, no data
    else:
        volume_ratio = float(latest_volume / avg_volume_20)
        volume_confidence = min(max(volume_ratio, 0.4), 1.5) / 1.5

    directional_score = (trend_score * (0.40 / 0.75)) + (momentum_score * (0.35 / 0.75))
    technical_score = directional_score * volume_confidence

    # Reported alongside technical_score, not folded into its formula - this
    # is a display/interpretation metric (see _up_down_volume_ratio's
    # docstring for why it's a volume-based proxy, not true order-flow),
    # kept independent so it doesn't get overshadowed by (or duplicate) the
    # existing volume_ratio factor above, which measures something different
    # (today's volume vs. its own recent average, not up-day vs. down-day split).
    buy_sell_ratio = _up_down_volume_ratio(closes, volumes)

    return {
        "price": price,
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2) if ma200 is not None else None,
        "rsi14": round(rsi14, 2) if rsi14 is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "buy_sell_ratio": round(buy_sell_ratio, 2) if buy_sell_ratio is not None else None,
        "technical_score": round(max(-100.0, min(100.0, technical_score)), 2),
    }
