import sys
import os
import json

# Add project root to path so we can run this directly
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "../..")))

from src.astro.alpha_analyzer import analyze_company_alpha

def run_test():
    print("==================================================")
    print("Astro-Financial Compilation Test (AAPL & Reliance)")
    print("==================================================")
    
    for ticker in ["AAPL", "RELIANCE.NS"]:
        print(f"\n[*] Running analysis for {ticker}...")
        try:
            result = analyze_company_alpha(ticker)
            if result.get("status") == "error":
                print(f"[!] Error: {result.get('message')}")
            else:
                print(f"[+] Analysis Complete for {result['company_name']} ({result['ticker']})")
                print(f"    Inc. Date:  {result['incorporation_date']} ({result['city']}, {result['country']})")
                print(f"    Lagna:      {result['lagna']}")
                print(f"    Nakshatra:  {result['moon_nakshatra']}")
                print(f"    Dasha:      {result['current_mahadasha']} Mahadasha - {result['current_bhukti']} Bhukti")
                print(f"    Financial Quality Score: {result['financial_quality']}/100  (AVS Fragility: {result['avs_score']})")
                print(f"    Astro Growth Score:      {result['astro_growth_score']}/100")
                print(f"    Unified Alpha Score:     {result['unified_alpha_score']}/100")
                print(f"    Interpreted Call:        {result['call_recommendation']} ({result['call_color']})")
                print(f"    Description:             {result['call_description']}")
        except Exception as e:
            print(f"[!] Test Crashed: {e}")

if __name__ == "__main__":
    run_test()
