import yfinance as yf
import pandas as pd
import numpy as np

def collect_us_forensic_data():
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'AVGO', 'AMD', 'NFLX',
        'ADBE', 'CRM', 'ORCL', 'INTC', 'QCOM', 'NOW', 'INTU', 'UBER', 'PANW', 'ABNB'
    ]
    
    print(f"[*] Auditing {len(tickers)} US Tech Entities (V10.0 Standard)...")
    forensic_data = []
    
    for symbol in tickers:
        print(f"    - Auditing: {symbol}")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Fetch for V10.0 Tiers
            current_price = info.get('currentPrice', 0)
            ebitda = info.get('ebitda', 1e-6) # prevent div by zero
            total_debt = info.get('totalDebt', 0)
            lvr = total_debt / ebitda if ebitda > 0 else 10.0 # High stress if negative ebitda
            
            # Z-Score Proxy (Working Cap / Total Assets etc)
            # For this audit, we'll use a standardized risk coefficient 
            z_score = info.get('quickRatio', 1.0) * 1.5 # Solvency proxy
            
            # MSR/FSR (Manual extraction for top 20)
            # We'll use the Sloan as a proxy for MSR in this fast scan
            bs = ticker.balance_sheet
            cf = ticker.cashflow
            total_assets = bs.iloc[0, 0] if not bs.empty else 1e9
            net_income = info.get('netIncomeToCommon', 0)
            ocf = cf.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cf.index else 0
            sloan = (net_income - ocf) / total_assets
            
            forensic_data.append({
                'Ticker': symbol,
                'Price': current_price,
                'Z_Score': round(z_score, 2),
                'LVR': round(lvr, 2),
                'MSR': round(sloan * 10, 2), # Normalized proxy
                'FSR': 5 if sloan < 0.1 else 3, # Operational health proxy
                'PE_Ratio': info.get('trailingPE', 0),
                'Short_Float': info.get('shortPercentOfFloat', 0) * 100
            })
            
        except Exception as e:
            print(f"    [!] Skip {symbol}: {e}")
            
    df = pd.DataFrame(forensic_data)
    df.to_csv("US_FORENSIC_RAW.csv", index=False)
    return df

if __name__ == "__main__":
    collect_us_forensic_data()
