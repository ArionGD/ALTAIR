from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd

class ROICEngine:
    """
    ALTAIR: Capital Efficiency Forensic Engine (The 'ROIC').
    Formula: NOPAT (Net Operating Profit After Tax) / Invested Capital.
    
    A Score < 0.10 (10%) indicates 'Wealth Destruction'—meaning the
    company is effectively burning shareholder value even if it's
    growing revenues.
    """

    def __init__(self):
        self.auditor = SovereignAuditor()

    def calculate_roic(self, ticker_symbol):
        print(f"[*] Auditing Capital Efficiency (ROIC) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        
        try:
            # 1. Fetch Key Data
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            
            if financials.empty or balance_sheet.empty:
                print(f"    [!] Warning: Finance data incomplete for {ticker_symbol}.")
                return 0.0

            # 2. Extract Data components
            operating_income = financials.loc['Operating Income'].iloc[0]
            tax_rate = financials.loc['Tax Provision'].iloc[0] / financials.loc['Pretax Income'].iloc[0]
            
            # Invested Capital logic (Total Assets - Non-interest liabilities)
            total_assets = balance_sheet.loc['Total Assets'].iloc[0]
            total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[0]
            total_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
            
            non_interest_liabilities = total_liabilities - total_debt
            invested_capital = total_assets - non_interest_liabilities
            
            # 3. NOPAT Calculation
            nopat = operating_income * (1 - tax_rate)
            
            # 4. Final ROIC Logic
            roic = nopat / invested_capital
            
            print(f"    [+] ROIC: {round(roic * 100, 2)}% ({'VALUE DESTROYER' if roic < 0.1 else 'WEALTH CREATOR'})")
            return round(float(roic), 4)

        except Exception as e:
            print(f"    [!] ROIC Audit Error for {ticker_symbol}: {e}")
            return 0.0

if __name__ == "__main__":
    engine = ROICEngine()
    # Test on a known 'Growth' target
    engine.calculate_roic("NYKAA.NS")
    # Test on an Efficiency Beast
    engine.calculate_roic("AAPL")
