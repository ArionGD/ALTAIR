from src.engine.hunter.SovereignAuditor import SovereignAuditor
import pandas as pd

class PiotroskiScoreEngine:
    """
    ALTAIR: Internal Strength Forensic Engine (The 'Piotroski F-Score').
    A 9-point system to detect financial health vs. decay.
    
    Score 0-2 = High Risk (The Sacrifice).
    Score 8-9 = Iron Fortress.
    """

    def __init__(self, auditor=None):
        self.auditor = auditor or SovereignAuditor()

    def calculate_piotroski_score(self, ticker_symbol):
        print(f"[*] Auditing Operating Integrity (Piotroski F-Score) for {ticker_symbol}...")
        ticker = self.auditor.get_ticker_object(ticker_symbol)
        
        try:
            # 1. Fetch Financials (Latest 2 years)
            financials = ticker.financials
            cashflow = ticker.cashflow
            balance_sheet = ticker.balance_sheet
            
            if financials.empty or cashflow.empty or balance_sheet.empty:
                print(f"    [!] Warning: Data incomplete for {ticker_symbol}.")
                return 4 # Neutral/Average
            
            # Extract Net Income, CFO, Total Assets for current and previous year
            f_score = 0
            
            # --- I. Profitability (4 pts) ---
            net_income = financials.loc['Net Income'].iloc[0]
            prev_net_income = financials.loc['Net Income'].iloc[1] if len(financials.columns) > 1 else net_income
            cfo = cashflow.loc['Operating Cash Flow'].iloc[0]
            total_assets = balance_sheet.loc['Total Assets'].iloc[0]
            prev_total_assets = balance_sheet.loc['Total Assets'].iloc[1] if len(balance_sheet.columns) > 1 else total_assets
            
            roa = net_income / total_assets
            prev_roa = prev_net_income / prev_total_assets
            
            if net_income > 0: f_score += 1 # 1. Pos Net Income
            if cfo > 0: f_score += 1        # 2. Pos CFO
            if roa > prev_roa: f_score += 1 # 3. Improvement in ROA
            if cfo > net_income: f_score += 1 # 4. Accrual quality (CFO > NI)
            
            # --- II. Leverage/Liquidity (3 pts) ---
            lt_debt = balance_sheet.loc['Total Debt'].iloc[0] if 'Total Debt' in balance_sheet.index else 0
            prev_lt_debt = balance_sheet.loc['Total Debt'].iloc[1] if 'Total Debt' in balance_sheet.index and len(balance_sheet.columns) > 1 else 0

            if lt_debt < prev_lt_debt: f_score += 1 # 5. Lower leverage

            # 6. Current Ratio improvement
            curr_assets = balance_sheet.loc['Current Assets'].iloc[0] if 'Current Assets' in balance_sheet.index else None
            curr_liabs = balance_sheet.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in balance_sheet.index else None
            prev_curr_assets = balance_sheet.loc['Current Assets'].iloc[1] if 'Current Assets' in balance_sheet.index and len(balance_sheet.columns) > 1 else None
            prev_curr_liabs = balance_sheet.loc['Current Liabilities'].iloc[1] if 'Current Liabilities' in balance_sheet.index and len(balance_sheet.columns) > 1 else None

            if curr_assets is not None and curr_liabs and prev_curr_assets is not None and prev_curr_liabs:
                current_ratio = curr_assets / curr_liabs
                prev_current_ratio = prev_curr_assets / prev_curr_liabs
                if current_ratio > prev_current_ratio: f_score += 1 # 6. Improved liquidity

            # 7. No new share issuance (dilution check)
            shares_out = balance_sheet.loc['Share Issued'].iloc[0] if 'Share Issued' in balance_sheet.index else None
            prev_shares_out = balance_sheet.loc['Share Issued'].iloc[1] if 'Share Issued' in balance_sheet.index and len(balance_sheet.columns) > 1 else None

            if shares_out is not None and prev_shares_out is not None:
                if shares_out <= prev_shares_out: f_score += 1 # 7. No dilution
            
            # --- III. Operating Efficiency (2 pts) ---
            gross_profit = financials.loc['Gross Profit'].iloc[0]
            prev_gross_profit = financials.loc['Gross Profit'].iloc[1] if len(financials.columns) > 1 else gross_profit
            revenue = financials.loc['Total Revenue'].iloc[0]
            prev_revenue = financials.loc['Total Revenue'].iloc[1] if len(financials.columns) > 1 else revenue
            
            gm = gross_profit / revenue
            prev_gm = prev_gross_profit / prev_revenue
            at = revenue / total_assets
            prev_at = prev_revenue / prev_total_assets
            
            if gm > prev_gm: f_score += 1 # 8. Improved margins
            if at > prev_at: f_score += 1 # 9. Improved asset turnover
            
            status = "AVERAGE"
            if f_score >= 7: status = "IRON FORTRESS"
            elif f_score <= 3: status = "SACRIFICE"
            
            print(f"    [+] Piotroski F-Score: {f_score}/9 ({status})")
            return f_score

        except Exception as e:
            print(f"    [!] F-Score Audit Error for {ticker_symbol}: {e}")
            return 4

if __name__ == "__main__":
    engine = PiotroskiScoreEngine()
    engine.calculate_piotroski_score("NYKAA.NS")
    engine.calculate_piotroski_score("TCS.NS")
