import os
import glob
import pandas as pd

# Oil-price exposure beta per (sector, sub_sector): how much operating margin
# pressure a name in this bucket faces per 1% rise in oil price, relative to
# a market-average name (beta = 1.0). Grounded in cost-structure logic:
# - Fuel/crude is a direct input cost (transport, chemicals, airlines-adjacent
#   industrials) -> high beta.
# - Fossil energy producers benefit from higher oil prices -> negative beta
#   (they are NOT fragile to an oil spike, they gain).
# - Renewable energy becomes relatively MORE attractive as fossil costs rise
#   -> negative/low beta.
# - Sectors with little direct fuel/commodity linkage (IT services, BFSI,
#   pharma, telecom, beauty/D2C) -> low beta, shock passes through only via
#   second-order effects (higher inflation/rates), not modeled here.
OIL_BETA = {
    ("Energy_Fossil", "Upstream_Integrated"): -0.9,
    ("Energy_Fossil", "Integrated_Majors"): -0.9,
    ("Energy_Fossil", "Downstream_Distribution"): -0.3,
    ("Energy_Fossil", "Refining_Services"): -0.2,

    ("Energy_Renewable", "Green_Generation"): -0.4,
    ("Energy_Renewable", "Solar"): -0.4,
    ("Energy_Renewable", "Financing_Grid"): -0.2,
    ("Energy_Renewable", "Grid_Storage_Other"): -0.2,

    ("Infra", "Transport_Logistics"): 1.0,
    ("Infra", "Construction_Cement"): 0.6,
    ("Infra", "Industrial_Capital_Goods"): 0.5,
    ("Infra", "Capital_Goods_Defense"): 0.3,

    ("Auto", "Legacy_ICE"): 0.7,
    ("Auto", "Commercial_Ancillary"): 0.6,
    ("Auto", "EV_Growth"): -0.3,
    ("Auto", "Passenger_Two_Wheeler"): 0.4,

    ("Materials_Metals", "Chemicals"): 0.8,
    ("Materials_Metals", "Steel_Mining"): 0.5,

    ("Consumer_Tech_Beauty", "Consumer_Internet"): 0.5,   # Delivery/logistics-heavy (fuel cost in unit economics)
    ("Consumer_Tech_Beauty", "New_Age_Internet"): 0.5,
    ("Consumer_Tech_Beauty", "Beauty_Retail"): 0.2,
    ("Consumer_Tech_Beauty", "Beauty_D2C"): 0.2,

    ("BFSI", "Money_Center_Banks"): 0.1,
    ("BFSI", "Investment_Markets"): 0.1,
    ("BFSI", "Private_Banks"): 0.1,
    ("BFSI", "PSU_NBFC"): 0.1,

    ("IT_Service", "Global_IT_Services"): 0.05,
    ("IT_Service", "Indian_Offshore_ADR"): 0.05,
    ("IT_Service", "Tier1_IT"): 0.05,
    ("IT_Service", "Tier2_IT"): 0.05,

    ("Health", "Pharma"): 0.1,
    ("Health", "Providers_Devices"): 0.1,
    ("Health", "Pharma_Generics"): 0.1,
    ("Health", "Hospitals_Diagnostics"): 0.1,

    ("Telecom_Media", "Telecom_Carriers"): 0.1,
    ("Telecom_Media", "Media_Streaming"): 0.1,
    ("Telecom_Media", "Media_Entertainment"): 0.1,
}

DEFAULT_BETA = 0.3  # unclassified sub-sector: assume mild, market-average exposure


def get_oil_beta(sector, sub_sector):
    return OIL_BETA.get((sector, sub_sector), DEFAULT_BETA)


class OilShockEngine:
    """
    ALTAIR: Scenario Exposure Layer — Oil Price Shock.
    Combines each ticker's existing fragility score (from the unified V11
    pipeline) with its oil-price exposure beta to classify how it would
    behave if oil moves from a baseline to a target price.

    This does NOT replace the fragility score — it answers a different
    question: "given a shock, who breaks vs. who just wobbles and recovers."
    """
    def __init__(self, processed_dir="data/processed"):
        self.processed_dir = processed_dir
        self.master_file = os.path.join(processed_dir, "GLOBAL_STRIKE_MAP_2026.csv")

    def load_master(self):
        if not os.path.exists(self.master_file):
            return None
        return pd.read_csv(self.master_file)

    def classify_scored_dataframe(self, df, baseline_price=80.0, target_price=100.0):
        """Applies oil-exposure beta + quadrant classification to an
        already-scored dataframe (must have market/sector/sub_sector/
        astra_strike_score columns) — shared by both the broad master-file
        path and the Analytics tab's on-demand scoped-scoring path."""
        if df.empty:
            return df

        pct_move = (target_price - baseline_price) / baseline_price  # e.g. +0.25 for $80->$100

        df = df.copy()
        df['oil_beta'] = df.apply(lambda r: get_oil_beta(r['sector'], r.get('sub_sector', '')), axis=1)

        # Exposure score (0-100): magnitude of beta * shock size, scaled so a
        # beta=1.0 name facing a 25% oil move lands near the top of the scale.
        df['exposure_score'] = (df['oil_beta'] * pct_move * 100).clip(-100, 100)

        # Fragility is the existing forensic score (0-100, higher = weaker balance sheet).
        df['fragility_score'] = df['astra_strike_score']

        # Quadrant classification: exposure direction/magnitude x fragility.
        def classify(row):
            exposure = row['exposure_score']
            fragility = row['fragility_score']
            if exposure >= 15 and fragility >= 50:
                return "HARD SHORT — fragile + directly exposed"
            if exposure >= 15 and fragility < 50:
                return "TEMPORARY CORRECTION — strong balance sheet, will recover"
            if exposure < 15 and exposure > -15 and fragility >= 50:
                return "WEAK BUT DORMANT — fragile, not this scenario"
            if exposure <= -15:
                return "BENEFICIARY — gains from this shock"
            return "RESILIENT — low exposure, low fragility"

        df['scenario_verdict'] = df.apply(classify, axis=1)

        return df[[
            'ticker', 'market', 'sector', 'sub_sector', 'oil_beta',
            'exposure_score', 'fragility_score', 'astra_strike_score', 'scenario_verdict'
        ]].sort_values(by='exposure_score', ascending=False)

    def run_scenario(self, baseline_price=80.0, target_price=100.0, market=None, sector=None, sub_sector=None):
        """Broad path: classifies whatever's already in the headline strike map."""
        df = self.load_master()
        if df is None:
            return None

        if market:
            df = df[df['market'].str.upper() == market.upper()]
        if sector:
            df = df[df['sector'] == sector]
        if sub_sector:
            df = df[df['sub_sector'] == sub_sector]

        return self.classify_scored_dataframe(df, baseline_price, target_price)


if __name__ == "__main__":
    engine = OilShockEngine()
    result = engine.run_scenario(baseline_price=80.0, target_price=100.0)
    if result is not None:
        print(result.head(20).to_string(index=False))
    else:
        print("[!] No strike map found — run /api/v1/audit first.")
