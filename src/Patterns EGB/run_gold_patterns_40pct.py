"""
Third glass-box pattern-finding pass, on the 40% enrichment tier
(data/raw/Gold/GOLD_MASTER_40PCT.csv) — adds fed_funds_change_90d (the
rolling cumulative Fed rate move, i.e. "is the Fed in a hiking or cutting
cycle") on top of the 30% tier's factors.

Same method as the earlier runs (XGBoost + SHAP, chronological
train/test split) — exists to compare against the 30% tier's R^2/factor
ranking and see whether the sustained-rate-cycle signal adds anything
the single-day fed_funds_change couldn't.
"""
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from sklearn.metrics import r2_score

from result_writer import write_tier_summary

GOLD_MASTER_40PCT = os.path.join("data", "raw", "Gold", "GOLD_MASTER_40PCT.csv")
RESULT_DIR = os.path.join("data", "raw", "Gold")


def load_data():
    df = pd.read_csv(GOLD_MASTER_40PCT, parse_dates=["date"])
    df["fed_funds_change"] = df["fed_funds_rate"].diff()
    df = df.dropna(subset=["fed_funds_change"])
    return df


def run_patterns():
    df = load_data()

    features = [
        "oil_return", "fed_funds_rate", "fed_funds_change", "fed_funds_change_90d",
        "real_10y_yield", "real_10y_yield_change",
        "dollar_index_return",
    ]
    X = df[features]
    y = df["gold_return"]

    split_idx = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        random_state=42,
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    r2 = r2_score(y_test, pred)

    print(f"[*] Trained on {len(X_train)} days, tested on {len(X_test)} days (chronological split)")
    print(f"[*] Out-of-sample R^2 (40% tier, 7 factors): {r2:.4f}")
    print("    Compare against the 30% tier's R^2 of 0.109 (6 factors, no rate-cycle momentum).")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)

    mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
    importance = pd.DataFrame({
        "factor": features,
        "mean_abs_shap_impact": mean_abs_shap,
    }).sort_values("mean_abs_shap_impact", ascending=False)

    print("\n=== Factor importance (mean |SHAP value|, higher = more explanatory) ===")
    print(importance.to_string(index=False))

    print("\n=== Direction check (correlation between feature value and its SHAP contribution) ===")
    direction_map = {}
    for i, feat in enumerate(features):
        corr = np.corrcoef(X_test[feat], shap_values.values[:, i])[0, 1]
        direction = "same direction (+)" if corr > 0 else "opposite direction (-)"
        direction_map[feat] = {"correlation": round(float(corr), 3), "direction": direction}
        print(f"    {feat}: corr={corr:.3f}  ->  {direction}")

    output_path = os.path.join(RESULT_DIR, "GOLD_PATTERNS_RESULT_40PCT.csv")
    importance.to_csv(output_path, index=False)
    print(f"\n[+] Factor importance saved: {output_path}")

    write_tier_summary(
        RESULT_DIR, "GOLD_40PCT", r2, len(X_train), len(X_test),
        df["date"].iloc[0], df["date"].iloc[-1], importance, direction_map,
    )

    return importance, r2


if __name__ == "__main__":
    run_patterns()
