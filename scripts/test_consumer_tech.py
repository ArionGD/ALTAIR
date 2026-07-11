import pandas as pd
import time
import os
from src.engine.hunter.DataCollector import GlobalBilateralCollector
from src.engine.hunter.VulnerabilityRanker import VulnerabilityRanker

def run_consumer_tech_test():
    print("\n" + "="*80)
    print("      🏛️ ALTAIR: INDIAN CONSUMER TECH & BEAUTY FORENSIC TEST (V10.0)     ")
    print("="*80)
    
    # 1. Targeted Data Collection (Only valid tickers to avoid 404s)
    collector = GlobalBilateralCollector()
    collector.markets = {
        "IND": {"Consumer_Tech_Beauty": ["NYKAA.NS", "ZOMATO.NS", "PAYTM.NS", "POLICYBZR.NS", "DELHIVERY.NS", "HONASA.NS", "CARTRADE.NS"]}
    }
    
    print("[*] Collecting live metrics for the sector...")
    collector.run_global_audit()
    
    # 2. Ranking with AVS V10.0
    print("[*] Performing AVS V10.0 Sovereign Hard-Strike Audit...")
    ranker = VulnerabilityRanker()
    # We guide the ranker to only process the relevant folder
    ranker.raw_dir = "data/raw/IND/Consumer_Tech_Beauty"
    
    # Normally we do process_all_sectors, but here we do it for just this folder manually
    vulnerability_file = os.path.join(ranker.raw_dir, "IND_Consumer_Tech_Beauty_vulnerability.csv")
    if not os.path.exists(vulnerability_file):
        print(f"[X] No data found at {vulnerability_file}")
        return

    master_df = pd.read_csv(vulnerability_file)
    master_df['sector'] = 'Consumer_Tech_Beauty'
    
    results = []
    for index, row in master_df.iterrows():
        avs, z, m, f, ss, lev = ranker.calculate_avs_score_v10(row)
        results.append({
            'ticker': row['ticker'], 
            'avs_score': avs, 
            'z_score': z,
            'lvr': lev,
            'msr': m,
            'fsr': f,
            'ss_score': ss
        })
        time.sleep(2) # Extra Safety for NSE-Bridge
        
    final_df = pd.DataFrame(results).sort_values(by='ss_score', ascending=False)
    
    # 3. Output Table: Sovereign Hard-Finance Grade
    print("\n" + "-"*120)
    print("      🏛️ THE 'SOVEREIGN HARD-FINANCE' ANALYSIS (INDIAN CONSUMER TECH & BEAUTY)     ")
    print("-"*120)
    # Ticker | AVS | Z | LVR | MSR | FSR | SS %
    print(final_df[['ticker', 'avs_score', 'z_score', 'lvr', 'msr', 'fsr', 'ss_score']].to_string(index=False))
    print("-"*120)
    
    final_df.to_csv("ALTAIR_STRIKE_LIST_V10_TEST.csv", index=False)
    
    # Strategic Note
    top_target = final_df.iloc[0]['ticker']
    print(f"\n[!] STRATEGIC VERDICT: {top_target} is the Priority Strike for the April Reset.")
    print("="*80)

if __name__ == "__main__":
    run_consumer_tech_test()
