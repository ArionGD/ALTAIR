import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.append(PROJECT_ROOT)

from main import app

client = TestClient(app)

def test_radar_signals():
    print("==================================================")
    print("Testing GET /api/v1/altair/signals/radar")
    print("==================================================")
    
    response = client.get("/api/v1/altair/signals/radar")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    data = response.json()
    assert "signals" in data
    signals = data["signals"]
    print(f"Retrieved {len(signals)} swing signals:")
    for s in signals:
        print(f"  - {s['ticker']} [{s['direction']}]: Entry {s['entry_price']}, Target {s['target_price']}, StopLoss {s['stop_loss']} (Conviction: {s['conviction_score']}%)")
        print(f"    Rationale: {s['rationale']}")
        assert "ticker" in s
        assert "direction" in s
        assert "entry_price" in s
        assert "target_price" in s
        assert "stop_loss" in s
        assert "conviction_score" in s
        assert "rationale" in s
    print("[+] Radar signals check passed successfully!")

def test_sectors_scores():
    print("\n==================================================")
    print("Testing GET /api/v1/altair/sectors/scores")
    print("==================================================")
    
    response = client.get("/api/v1/altair/sectors/scores")
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    data = response.json()
    assert "sectors" in data
    sectors = data["sectors"]
    print(f"Retrieved {len(sectors)} sector diagnostic scorecards:")
    for sec in sectors:
        print(f"  - {sec['name']} ({sec['key']}): Score {sec['score']} | Health: {sec['health']}")
        print(f"    Metrics: {sec['metrics']}")
        assert "name" in sec
        assert "key" in sec
        assert "score" in sec
        assert "health" in sec
        assert "metrics" in sec
    print("[+] Sectors scores check passed successfully!")

def test_stress_test():
    print("\n==================================================")
    print("Testing POST /api/v1/altair/scenario/stress-test")
    print("==================================================")
    
    payload = {
        "scenario": "crude_oil_spike_20",
        "portfolio": [
            {"ticker": "RELIANCE.NS", "shares": 100},
            {"ticker": "TCS.NS", "shares": 50},
            {"ticker": "ADANIPORTS.NS", "shares": 150}
        ]
    }
    
    response = client.post("/api/v1/altair/scenario/stress-test", json=payload)
    print(f"Status Code: {response.status_code}")
    assert response.status_code == 200
    
    data = response.json()
    print(f"Scenario: {data['scenario']}")
    print(f"Total Current Value:   {data['total_current_value']}")
    print(f"Total Projected Value: {data['total_projected_value']}")
    print(f"Projected P&L Impact:  {data['projected_pnl_impact']}")
    print(f"Projected Return %:    {data['projected_return_pct']}%")
    print(f"Hedging Advice:        {data['hedging_advice']}")
    
    assert data["scenario"] == "crude_oil_spike_20"
    assert data["total_current_value"] > 0
    assert "holdings_impact" in data
    
    for h in data["holdings_impact"]:
        print(f"  - {h['ticker']}: Price {h['current_price']}, Impact {h['projected_change_pct']}%, P&L {h['projected_pnl_impact']} ({h['verdict']})")
        assert "ticker" in h
        assert "current_price" in h
        assert "projected_change_pct" in h
        assert "projected_pnl_impact" in h
        assert "verdict" in h
        
    print("[+] Macro scenario stress test check passed successfully!")

if __name__ == "__main__":
    test_radar_signals()
    test_sectors_scores()
    test_stress_test()
