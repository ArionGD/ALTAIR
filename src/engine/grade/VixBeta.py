import yfinance as yf
import pandas as pd
import numpy as np

class VixBetaEngine:
    """
    ALTAIR: Liquefaction Beta Module.
    Measures the 'Panic Sensitivity' of a stock.
    Higher Beta = Faster Crater during a VIX Spike.
    """

    def calculate_vix_sensitivity(self, ticker_symbol, period="1y"):
        print(f"[*] Analyzing VIX Beta (Panic Sensitivity) for {ticker_symbol}...")
        
        # Fetch Stock and VIX History
        data = yf.download([ticker_symbol, "^VIX"], period=period, interval="1d")['Close']
        returns = data.pct_change().dropna()
        
        if returns.empty:
            return 0.0
            
        # Calculate Correlation and Covariance
        # A positive VIX Beta means the stock falls when VIX rises (Inverse Correlation)
        stock_returns = returns[ticker_symbol]
        vix_returns = returns["^VIX"]
        
        correlation = stock_returns.corr(vix_returns)
        
        # Higher absolute correlation with VIX often indicates a 'Liquidation' candidate.
        # We normalize this to a 0-10 sensitivity score
        panic_sensitivity = abs(correlation) * 10
        
        return round(panic_sensitivity, 2)

if __name__ == "__main__":
    engine = VixBetaEngine()
    print(f"Panic Score (NVDA): {engine.calculate_vix_sensitivity('NVDA')}")
    print(f"Panic Score (PEP): {engine.calculate_vix_sensitivity('PEP')}")
