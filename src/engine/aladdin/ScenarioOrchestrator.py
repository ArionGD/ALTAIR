import pandas as pd

class ScenarioOrchestrator:
    """
    ALTAIR: Operation Aladdin (Simulation Engine).
    Calculates the impact of Global Scenarios on the ALTAIR Portfolio.
    """
    def __init__(self, matrix_path="SensitivityMatrix.csv"):
        self.df = pd.read_csv(matrix_path)
        
    def run_simulation(self, scenario_name):
        print(f"[*] ALTAIR Aladdin: Simulating Scenario -> [{scenario_name.upper()}]")
        
        # Scenario Weight Definitions
        scenarios = {
            'taiwan_crisis': {
                'Energy_Beta': 0.2,
                'Semi_Beta': 1.0,  # Max Impact
                'FII_Beta': 0.5,
                'VIX_Beta': 0.8
            },
            'oil_spike': {
                'Energy_Beta': 1.0, # Max Impact
                'Semi_Beta': 0.1,
                'FII_Beta': 0.6,
                'VIX_Beta': 0.5
            },
            'exodus': {
                'Energy_Beta': 0.4,
                'Semi_Beta': 0.4,
                'FII_Beta': 1.0, # Max Impact
                'VIX_Beta': 0.7
            }
        }
        
        if scenario_name not in scenarios:
            print(f"[!] Scenario '{scenario_name}' not defined.")
            return

        weights = scenarios[scenario_name]
        
        # Calculation: Impact = (Sum of Beta * Weight) * Forensic_Weight
        # Higher score = Higher Fracture (Better for Put Options)
        
        self.df['Impact_Score'] = (
            (self.df['Energy_Beta'] * weights['Energy_Beta']) +
            (self.df['Semi_Beta'] * weights['Semi_Beta']) +
            (self.df['FII_Beta'] * weights['FII_Beta']) +
            (self.df['VIX_Beta'] * weights['VIX_Beta'])
        ) * (1 + self.df['Forensic_Weight'])
        
        # Sort by Impact Score (The highest fracture candidates)
        self.df = self.df.sort_values(by='Impact_Score', ascending=False)
        
        output_file = f"ALADDIN_SIM_{scenario_name.upper()}.csv"
        self.df[['Ticker', 'Impact_Score']].to_csv(output_file, index=False)
        
        print(f"[+] Simulation Complete. Top 5 Fracture Targets for {scenario_name}:")
        print(self.df[['Ticker', 'Impact_Score']].head(5).to_string(index=False))
        return self.df

if __name__ == "__main__":
    orchestrator = ScenarioOrchestrator()
    # Run the Taiwan Crisis Simulation
    orchestrator.run_simulation('taiwan_crisis')
    # Run the Oil Spike Simulation
    orchestrator.run_simulation('oil_spike')
