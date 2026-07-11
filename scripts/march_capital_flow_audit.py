import yfinance as yf
import pandas as pd

def audit_march_capital_flows():
    """
    ALTAIR Aladdin: March 2026 Capital Flow Forensic Audit.
    Tracks where institutional money moved during the war escalation.
    """
    
    # Asset Classes to Track
    assets = {
        # Equities (Tech / Growth)
        'TSLA': 'US Tech (Tesla)',
        'NVDA': 'US Tech (NVIDIA)',
        'AAPL': 'US Tech (Apple)',
        'MSFT': 'US Tech (Microsoft)',
        'DELHIVERY.NS': 'India Tech (Delhivery)',
        'NYKAA.NS': 'India Tech (Nykaa)',
        'PAYTM.NS': 'India Tech (Paytm)',
        
        # Indices
        '^GSPC': 'S&P 500 Index',
        '^NSEI': 'Nifty 50 Index',
        '^DJI': 'Dow Jones Index',
        
        # Safe Havens
        'GC=F': 'Gold Futures',
        'SI=F': 'Silver Futures',
        
        # Bonds / Dollar
        'TLT': 'US Treasury Bond ETF (20Y)',
        'DX-Y.NYB': 'US Dollar Index',
        
        # Energy Commodities
        'CL=F': 'Crude Oil (WTI)',
        'BZ=F': 'Brent Crude Oil',
        
        # US Energy Stocks
        'XOM': 'US Energy (ExxonMobil)',
        'CVX': 'US Energy (Chevron)',
        'OXY': 'US Energy (Occidental)',
        'COP': 'US Energy (ConocoPhillips)',
        'SLB': 'US Energy (Schlumberger)',
        'HAL': 'US Energy (Halliburton)',
        
        # India Energy Stocks
        'RELIANCE.NS': 'India Energy (Reliance)',
        'ONGC.NS': 'India Energy (ONGC)',
        'IOC.NS': 'India Energy (Indian Oil)',
        'BPCL.NS': 'India Energy (BPCL)',
        'GAIL.NS': 'India Energy (GAIL)',
        'ADANIGREEN.NS': 'India Energy (Adani Green)',
        
        # Gulf Energy (The Petro-Fortress)
        '2222.SR': 'Gulf Energy (Saudi Aramco)',
        'ADNOCDIST.AD': 'Gulf Energy (ADNOC Distribution)',
    }
    
    print("=" * 70)
    print("  ALTAIR ALADDIN: MARCH 2026 CAPITAL FLOW FORENSIC AUDIT")
    print("=" * 70)
    
    results = []
    
    for ticker, name in assets.items():
        try:
            data = yf.Ticker(ticker)
            # Get March 2026 data (approx 1 month)
            hist = data.history(start="2026-03-01", end="2026-04-01")
            
            if hist.empty or len(hist) < 2:
                print(f"    [!] No data for {name} ({ticker})")
                continue
                
            open_price = round(hist['Close'].iloc[0], 2)
            close_price = round(hist['Close'].iloc[-1], 2)
            high = round(hist['High'].max(), 2)
            low = round(hist['Low'].min(), 2)
            change_pct = round(((close_price / open_price) - 1) * 100, 2)
            
            # Determine Flow Direction
            if change_pct > 3:
                flow = "INFLOW (Buying)"
            elif change_pct < -3:
                flow = "OUTFLOW (Selling)"
            else:
                flow = "NEUTRAL (Holding)"
            
            results.append({
                'Asset': name,
                'Ticker': ticker,
                'Mar_Open': open_price,
                'Mar_Close': close_price,
                'Mar_High': high,
                'Mar_Low': low,
                'Change_Pct': change_pct,
                'Capital_Flow': flow
            })
            
            print(f"    [+] {name}: {open_price} -> {close_price} ({change_pct}%) [{flow}]")
            
        except Exception as e:
            print(f"    [!] Error for {ticker}: {e}")
    
    # Save Results
    df = pd.DataFrame(results)
    df = df.sort_values(by='Change_Pct', ascending=True)
    df.to_csv("MARCH_2026_CAPITAL_FLOW_AUDIT.csv", index=False)
    
    print("\n" + "=" * 70)
    print("  SOVEREIGN VERDICT: CAPITAL MIGRATION SUMMARY")
    print("=" * 70)
    
    # Separate into categories
    outflows = df[df['Change_Pct'] < -3]
    inflows = df[df['Change_Pct'] > 3]
    neutral = df[(df['Change_Pct'] >= -3) & (df['Change_Pct'] <= 3)]
    
    print("\n  [OUTFLOW - Money LEFT these assets]:")
    for _, row in outflows.iterrows():
        print(f"    {row['Asset']}: {row['Change_Pct']}%")
    
    print("\n  [INFLOW - Money ENTERED these assets]:")
    for _, row in inflows.iterrows():
        print(f"    {row['Asset']}: +{row['Change_Pct']}%")
    
    print("\n  [NEUTRAL - Money HELD steady]:")
    for _, row in neutral.iterrows():
        print(f"    {row['Asset']}: {row['Change_Pct']}%")
    
    print(f"\n  [+] Full audit saved to MARCH_2026_CAPITAL_FLOW_AUDIT.csv")

if __name__ == "__main__":
    audit_march_capital_flows()
