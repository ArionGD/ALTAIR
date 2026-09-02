import yfinance as yf
import pandas as pd
import numpy as np
import math

print("[*] Testing 4-Pillar Sub-Field Swing Scanner (Auto 2-Wheelers)...")

# Define sample niche universe
NICHE_MAP = {
    "Auto - 2-Wheelers": ["BAJAJ-AUTO.NS", "TVSMOTOR.NS", "HEROMOTOCO.NS", "EICHERMOT.NS"],
    "Auto - 4W & CV": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS", "ASHOKLEY.NS", "BHARATFORG.NS"],
    "Banking - Private": ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "Banking - PSU": ["SBIN.NS", "BANKBARODA.NS", "PNB.NS", "CANBK.NS", "UNIONBANK.NS"],
    "IT - Large Cap": ["TCS.NS", "INFY.NS", "HCLTECH.NS", "WIPRO.NS", "TECHM.NS"],
    "Energy - Upstream & Power": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS"]
}

def scan_niche_field(field_name="Auto - 2-Wheelers"):
    tickers = NICHE_MAP.get(field_name, NICHE_MAP["Auto - 2-Wheelers"])
    results = []
    
    for ticker in tickers:
        print(f"[*] Scanning {ticker} in '{field_name}'...")
        t = yf.Ticker(ticker)
        
        # 1. Historical daily bars
        hist = t.history(period="1y")
        if hist.empty or len(hist) < 50:
            continue
            
        close = float(hist['Close'].iloc[-1])
        ma_20 = float(hist['Close'].rolling(20).mean().iloc[-1])
        ma_50 = float(hist['Close'].rolling(50).mean().iloc[-1])
        ma_200 = float(hist['Close'].rolling(200).mean().iloc[-1]) if len(hist) >= 200 else ma_50
        
        # Wilder's RSI(14)
        delta = hist['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])
        
        # ATR 14
        tr = pd.concat([
            hist['High'] - hist['Low'],
            (hist['High'] - hist['Close'].shift()).abs(),
            (hist['Low'] - hist['Close'].shift()).abs()
        ], axis=1).max(axis=1)
        atr = float(tr.rolling(14).mean().iloc[-1])
        
        # Fundamentals from info
        info = t.info or {}
        pe = info.get('trailingPE') or info.get('forwardPE') or 20.0
        de = info.get('debtToEquity') or 20.0 # debt to equity in %
        roe = (info.get('returnOnEquity') or 0.15) * 100
        op_margin = (info.get('operatingMargins') or 0.12) * 100
        
        # Fundamental Score (0-100, higher is better/healthier)
        fund_score = 50.0
        if de < 50: fund_score += 20
        elif de < 100: fund_score += 10
        if roe > 15: fund_score += 15
        if op_margin > 12: fund_score += 15
        fund_score = min(100, max(10, fund_score))
        
        # Technical Momentum Score (0-100)
        tech_score = 50.0
        if close > ma_50: tech_score += 20
        if ma_50 > ma_200: tech_score += 15
        if close > ma_20: tech_score += 15
        tech_score = min(100, max(10, tech_score))
        
        # RSI Momentum Rating (0-100) - sweet spot is 45-65
        if 45 <= rsi <= 65:
            rsi_score = 90.0 # prime momentum continuation
        elif rsi < 35:
            rsi_score = 80.0 # oversold bounce candidate
        elif rsi > 70:
            rsi_score = 40.0 # overbought pullback risk
        else:
            rsi_score = 60.0
            
        # Gann Alignment: Time from last major high/low & Square of 9 support
        # Find latest swing pivot (last 30 days min/max)
        recent_30 = hist.tail(30)
        pivot_low = float(recent_30['Low'].min())
        pivot_high = float(recent_30['High'].max())
        
        # Square of 9 nearest floor
        sqrt_p = math.sqrt(close)
        sq9_floor = round((sqrt_p - 0.25) ** 2, 2) # -45 deg floor
        sq9_dist_pct = abs((close - sq9_floor) / close) * 100
        
        gann_score = 65.0
        if sq9_dist_pct < 1.5:
            gann_score = 90.0 # right at key geometric floor
        elif sq9_dist_pct < 3.0:
            gann_score = 80.0
            
        # Combined Swing Opportunity Index (0-100)
        # Weights: 25% Fundamentals + 30% Momentum + 20% RSI + 25% Gann
        swing_index = (0.25 * fund_score) + (0.30 * tech_score) + (0.20 * rsi_score) + (0.25 * gann_score)
        
        target = round(close + (2.5 * atr), 2)
        stop_loss = round(close - (1.5 * atr), 2)
        
        verdict = "STRONG BUY" if swing_index >= 75 else ("BUY ON PULLBACK" if swing_index >= 60 else "NEUTRAL / WATCH")
        
        results.append({
            'Ticker': ticker,
            'Field': field_name,
            'CMP': round(close, 2),
            'Swing_Index': round(swing_index, 1),
            'Verdict': verdict,
            'Target_2.5ATR': target,
            'StopLoss_1.5ATR': stop_loss,
            'RSI_14': round(rsi, 1),
            'Fund_Score': round(fund_score, 0),
            'Tech_Score': round(tech_score, 0),
            'Gann_Score': round(gann_score, 0)
        })
        
    df_res = pd.DataFrame(results).sort_values(by='Swing_Index', ascending=False)
    return df_res

df_out = scan_niche_field("Auto - 2-Wheelers")
print("\n[+] Scan completed successfully! Ranked Opportunity Table:")
print(df_out[['Ticker', 'CMP', 'Swing_Index', 'Verdict', 'Target_2.5ATR', 'StopLoss_1.5ATR', 'RSI_14']])
