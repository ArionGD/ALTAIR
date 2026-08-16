import sys
import os

# Add project root to path
sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from src.engine.aries.aries_engine import run_aries_valuation, calculate_dcf_intrinsic_value

def test_calculations():
    print("==================================================")
    print("Running Intrinsic Value Calculator Math Checks")
    print("==================================================")
    
    # Check DCF Math
    res = calculate_dcf_intrinsic_value(
        fcf_0=100.0,
        shares_outstanding=10.0,
        total_debt=20.0,
        cash_equivalents=50.0,
        growth_rate_5yr=0.10,
        terminal_growth=0.03,
        wacc=0.08
    )
    print(f"[*] DCF calculation output:")
    print(f"    Enterprise Value: {res['enterprise_value']}")
    print(f"    Equity Value:     {res['equity_value']}")
    print(f"    Intrinsic Value:  {res['intrinsic_value']}")
    assert res["intrinsic_value"] > 0, "DCF intrinsic value must be positive"
    print("[+] DCF Math test passed successfully!")

def test_live_valuation():
    print("\n==================================================")
    print("Running Live yfinance Queries & Aries Evaluator")
    print("==================================================")
    
    for ticker in ["AAPL", "ITC.NS"]:
        print(f"\n[*] Evaluating {ticker}...")
        try:
            val = run_aries_valuation(ticker)
            if val.get("status") == "error":
                print(f"    [!] Error running valuation: {val.get('message')}")
                continue
                
            print(f"    CMP:                  {val['current_market_price']}")
            print(f"    Recommended Model:    {val['recommended_model']}")
            print(f"    Recommended Value:    {val['recommended_intrinsic_value']}")
            print(f"    Margin of Safety:     {val['margin_of_safety']['margin_of_safety_pct']}%")
            print(f"    Status:               {val['margin_of_safety']['status']}")
            print(f"    Action Recommended:   {val['margin_of_safety']['action']}")
            
            # Print individual model results
            print(f"    [Individual models]")
            print(f"      - DCF Value:        {val['models']['dcf']['intrinsic_value']}")
            print(f"      - Graham Value:     {val['models']['graham']['intrinsic_value']}")
            print(f"      - DDM Value:        {val['models']['ddm']['intrinsic_value']}")
        except Exception as e:
            print(f"    [!] Exception while evaluating {ticker}: {e}")

def test_upstox_mock():
    print("\n==================================================")
    print("Running Mocked Upstox API Parser Checks")
    print("==================================================")
    
    from unittest.mock import patch
    from src.engine.aries.upstox_client import fetch_upstox_financials
    
    mock_ltp = {
        "status": "success",
        "data": {
            "NSE_EQ:RELIANCE": {
                "last_price": 2400.0,
                "instrument_token": "NSE_EQ|INE002A01018"
            }
        }
    }
    
    mock_bs = {
        "status": "success",
        "data": {
            "history": [
                {
                    "total_asset": 150000.0, 
                    "total_liability": 70000.0,
                    "period": "Mar 2025"
                }
            ]
        }
    }
    
    mock_inc = {
        "status": "success",
        "data": {
            "income_statement": [
                {
                    "category": "revenue",
                    "history": [{"value": 90000.0}]
                },
                {
                    "category": "net_profit",
                    "history": [{"value": 15000.0}]
                },
                {
                    "category": "ebit",
                    "history": [{"value": 20000.0}]
                }
            ]
        }
    }
    
    mock_cf = {
        "status": "success",
        "data": {
            "cash_flow": [
                {
                    "category": "operating",
                    "history": [{"value": 18000.0}]
                },
                {
                    "category": "investing",
                    "history": [{"value": -6000.0}]
                }
            ]
        }
    }
    
    def side_effect(endpoint, params=None):
        if "market-quote/ltp" in endpoint:
            return mock_ltp
        elif "balance-sheet" in endpoint:
            return mock_bs
        elif "income-statement" in endpoint:
            return mock_inc
        elif "cash-flow" in endpoint:
            return mock_cf
        return {"status": "error"}
        
    with patch("src.engine.aries.upstox_client.UPSTOX_ACCESS_TOKEN", "mocked_token"), \
         patch("src.engine.aries.upstox_client.call_upstox_api", side_effect=side_effect):
        
        val = fetch_upstox_financials("RELIANCE.NS")
        print("[*] Mocked Upstox fetch result:")
        print("    CMP:", val["cmp"])
        print("    FCF:", val["fcf_0"])
        print("    EPS:", val["eps"])
        print("    Debt:", val["total_debt"])
        
        assert val["cmp"] == 2400.0
        assert val["total_debt"] == 70000.0 * 10000000.0
        assert val["eps"] == (15000.0 * 10000000.0) / 6760000000.0
        print("[+] Mocked Upstox API test passed successfully!")

if __name__ == "__main__":
    test_calculations()
    test_upstox_mock()
    test_live_valuation()

