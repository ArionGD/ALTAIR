import yfinance as yf
import pandas as pd

def audit_us_tech_march_flows():
    """
    ALTAIR Aladdin: US Tech Top 20 - March 2026 Capital Flow Report.
    Identifies which 'Glass Pillars' in the US are being liquidated the hardest.
    """
    
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'AMD', 'NFLX',
        'ADBE', 'CRM', 'ORCL', 'INTC', 'QCOM', 'NOW', 'INTU', 'UBER', 'PANW', 'ABNB'
    ]
    
    print("=" * 70)
    print("  ALTAIR ALADDIN: US TECH TOP 20 - MARCH 2026 FLOW AUDIT")
    print("=" * 70)
    
    results = []
    
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            # Fetch March 2026 data
            hist = ticker.history(start="2026-03-01", end="2026-04-01")
            
            if hist.empty or len(hist) < 2:
                print(f"    [!] No data for {symbol}")
                continue
                
            open_price = round(hist['Close'].iloc[0], 2)
            close_price = round(hist['Close'].iloc[-1], 2)
            change_pct = round(((close_price / open_price) - 1) * 100, 2)
            
            # Categorization
            if change_pct > 2:
                flow = "INFLOW (Defensive Buying)"
            elif change_pct < -2:
                flow = "OUTFLOW (Liquidation)"
            else:
                flow = "NEUTRAL (Stability)"
            
            results.append({
                'Ticker': symbol,
                'Mar_Open': open_price,
                'Mar_Close': close_price,
                'Change_Pct': change_pct,
                'Capital_Flow': flow
            })
            
            print(f"    [+] {symbol}: {open_price} -> {close_price} ({change_pct}%) [{flow}]")
            
        except Exception as e:
            print(f"    [!] Error for {symbol}: {e}")
            
    # Save Report
    df = pd.DataFrame(results)
    # Sort by hardest liquidation first
    df = df.sort_values(by='Change_Pct', ascending=True)
    df.to_csv("US_TECH_MARCH_FLOW_REPORT.csv", index=False)
    
    print("\n" + "=" * 70)
    print("  SOVEREIGN SUMMARY: US TECH LIQUIDATION RANKING")
    print("=" * 70)
    
    for _, row in df.head(10).iterrows():
        print(f"    {row['Ticker']}: {row['Change_Pct']}% - {row['Capital_Flow']}")
        
    print(f"\n[+] Full US Tech audit saved to US_TECH_MARCH_FLOW_REPORT.csv")

if __name__ == "__main__":
    audit_us_tech_march_flows()
