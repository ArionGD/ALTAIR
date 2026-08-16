import pandas as pd
import os

def generate_global_bailout_audit():
    print("[*] Initializing Global Bilateral Bailout Audit (US & IND)...")
    
    # Forensic Classification Map (Fed/RBI Protection Levels)
    # 0-5% = The Sovereign Sacrifices (Tech Startups / Hype)
    # 80-100% = The Protected Guardians (Banks / Energy / Defense)
    bailout_map = {
        # 🇮🇳 IND Market: High Protection (PSUs / BFSI)
        "SBIN.NS": 100, "ONGC.NS": 100, "NTPC.NS": 100, "TCS.NS": 90, "INFY.NS": 85,
        "HDFCBANK.NS": 80, "ICICIBANK.NS": 80, "LT.NS": 80, "RELIANCE.NS": 80,
        
        # 🇮🇳 IND Market: The Sacrifices (Consumer Tech / Beauty)
        "ZOMATO.NS": 0, "PAYTM.NS": 0, "NYKAA.NS": 5, "HONASA.NS": 0, "DELHIVERY.NS": 5,
        "POLICYBZR.NS": 5, "CARTRADE.NS": 10,
        
        # 🇺🇸 US Market (Sovereign Floor)
        "INTC": 100, "BA": 100, "LMT": 100, "RTX": 100, "JPM": 100, "AAPL": 100,
        "TSLA": 15, "AMT": 10, "F": 20, "GM": 20, "ABNB": 15, "UBER": 15, "DASH": 10,
        "PATH": 5, "SNOW": 5, "PLTR": 20, "EL": 25, "ULTA": 20
    }

    base_dir = "../database/raw"
    results = []

    for market in ["US", "IND"]:
        market_dir = os.path.join(base_dir, market)
        if not os.path.exists(market_dir):
            continue
            
        for sector in os.listdir(market_dir):
            sector_path = os.path.join(market_dir, sector)
            file_path = os.path.join(sector_path, f"{market}_{sector}_vulnerability.csv")
            
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['market'] = market
                df['sector'] = sector
                
                # Apply Bailout Map & Calculate SS Score
                # If high PE and Low Bailout = High SS Score.
                df['bailout_probability'] = df['ticker'].map(bailout_map).fillna(30)
                df['astra_strike_score'] = df['pe_ratio'].clip(upper=300) / 3 + (100 - df['bailout_probability'])
                
                results.append(df)

    master_df = pd.concat(results, ignore_index=True)
    master_df = master_df.sort_values(by='astra_strike_score', ascending=False)
    
    # Save the Global Map
    output_path = "../database/processed/GLOBAL_STRIKE_MAP_2026.csv"
    master_df.to_csv(output_path, index=False)
    
    print(f"\n[+] Global Bilateral Strike Map Complete: {output_path}")
    print("\n=== TOP 10 GLOBAL STRIKES (BY SS_SCORE) ===")
    print(master_df[['ticker', 'market', 'pe_ratio', 'bailout_probability', 'astra_strike_score']].head(10))
    
    return output_path

if __name__ == "__main__":
    generate_global_bailout_audit()
