import yfinance as yf
import pandas as pd
import numpy as np

def audit_indian_valuations():
    """
    ALTAIR: Indian Market Bubble Audit.
    Ranks Indian companies by P/E, P/S, and Overvaluation Index.
    """
    
    # Target Tickers (High Hype + Major Sectors)
    tickers = [
        'PAYTM.NS', 'DELHIVERY.NS', 'NYKAA.NS', 'ZOMATO.NS', 'PBFINTECH.NS', 
        'TRENT.NS', 'TITAN.NS', 'ASIANPAINT.NS', 'ADANIENT.NS', 'ADANIGREEN.NS', 
        'ADANIPORTS.NS', 'TATAMOTORS.NS', 'MARUTI.NS', 'INDIGO.NS', 'RELIANCE.NS',
        'DMART.NS', 'HAL.NS', 'DLF.NS', 'DIXON.NS', 'POLYCAB.NS'
    ]
    
    print(f"[*] Auditing Valuation for {len(tickers)} Indian High-Value Targets...")
    audit_data = []
    
    for symbol in tickers:
        print(f"    - Analyzing: {symbol}")
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            price = info.get('currentPrice', 0)
            trailing_pe = info.get('trailingPE', np.nan)
            forward_pe = info.get('forwardPE', np.nan)
            price_to_sales = info.get('priceToSalesTrailing12Months', np.nan)
            market_cap = info.get('marketCap', 0)
            
            # For loss-making companies, trailing_pe is often not provided.
            # We use P/S as a secondary bubble metric.
            
            # 3. Fetch Cash Flow for Intrinsic Value
            cf = ticker.cashflow
            fcf = cf.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cf.index else 0
            if fcf == 0:
                fcf = cf.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cf.index else 0
            
            # --- Simplified Intrinsic Value (IV) Calculation ---
            # Formula: (FCF * (1 + g)) / (r - g)
            # r = Discount Rate (12% for India), g = Terminal Growth (5%)
            r = 0.12
            g = 0.05
            
            if fcf > 0:
                intrinsic_market_cap = (fcf * (1 + g)) / (r - g)
                intrinsic_price = intrinsic_market_cap / info.get('sharesOutstanding', 1)
            else:
                # For loss-making companies, we use a Book Value proxy or a very low floor
                intrinsic_price = info.get('bookValue', price * 0.2) 
            
            val_gap = ((price / intrinsic_price) - 1) * 100 if intrinsic_price > 0 else 0
            
            audit_data.append({
                'Ticker': symbol,
                'Price': price,
                'Intrinsic_Value': round(intrinsic_price, 2),
                'Valuation_Gap_Pct': round(val_gap, 2),
                'Market_Cap_Cr': round(market_cap / 1e7, 2),
                'PE_Trailing': trailing_pe,
                'PE_Forward': forward_pe,
                'Price_to_Sales': round(price_to_sales, 2) if not pd.isna(price_to_sales) else np.nan,
                'Sector': info.get('sector', 'N/A')
            })
            
        except Exception as e:
            print(f"    [!] Error auditing {symbol}: {e}")
            
    df = pd.DataFrame(audit_data)
    
    # --- Bubble Index Calculation ---
    df['PE_Score'] = df['PE_Trailing'].fillna(500) 
    df['PS_Score'] = df['Price_to_Sales'].fillna(1)
    df['Gap_Score'] = df['Valuation_Gap_Pct'].clip(0, 1000) # Weighting the overvaluation gap
    
    df['PE_Score'] = df['PE_Score'].apply(lambda x: min(x, 1000))
    
    # Updated Bubble Index including Valuation Gap (40% Gap, 40% PE, 20% PS)
    df['Bubble_Index'] = (
        (df['PE_Score'] / 1000 * 40) + 
        (df['PS_Score'] / df['PS_Score'].max() * 20) +
        (df['Gap_Score'] / df['Gap_Score'].max() * 40)
    ).round(2)
    
    df['Bubble_Index'] = (df['Bubble_Index'] / df['Bubble_Index'].max() * 100).round(2)
    df = df.sort_values(by='Bubble_Index', ascending=False)
    
    output_df = df[['Ticker', 'Price', 'Intrinsic_Value', 'Valuation_Gap_Pct', 'Market_Cap_Cr', 'PE_Trailing', 'Bubble_Index', 'Sector']]
    output_df.to_csv("INDIAN_VALUATION_BUBBLE_RANK.csv", index=False)
    
    print("\n[+] Audit Complete. Ranking saved to INDIAN_VALUATION_BUBBLE_RANK.csv")
    print("\nALTAIR TOP 10 OVERVALUED 'GLASS PILLARS' (INDIA):")
    print(output_df.head(10).to_string(index=False))

if __name__ == "__main__":
    audit_indian_valuations()
