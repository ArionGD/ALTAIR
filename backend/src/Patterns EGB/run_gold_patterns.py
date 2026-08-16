"""
First glass-box pattern-finding pass on the Gold Master sheet
(data/raw/Gold/GOLD_MASTER.csv).

Question: how much of gold's daily return is explained by oil's daily
return and the Fed funds rate level, and which factor matters more?

Model: XGBoost regressor, target = gold_return, features = [oil_return,
fed_funds_rate, fed_funds_rate_change]. Explained via SHAP values so the
output is auditable per-factor, not a black-box score.
"""
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score

from result_writer import write_tier_summary

GOLD_MASTER = os.path.join("data", "raw", "Gold", "GOLD_MASTER_10PCT.csv")
RESULT_DIR = os.path.join("data", "raw", "Gold")


def load_data():
    df = pd.read_csv(GOLD_MASTER, parse_dates=["date"])
    # Fed funds *level* isn't stationary (it trended 0.4 -> 5 -> 3.6 over the
    # window), so also include its day-over-day change as a feature —
    # otherwise the model can only learn "rate regime", not "rate moves".
    df["fed_funds_change"] = df["fed_funds_rate"].diff()
    df = df.dropna(subset=["fed_funds_change"])
    return df


def run_patterns():
    df = load_data()

    features = ["oil_return", "fed_funds_rate", "fed_funds_change"]
    X = df[features]
    y = df["gold_return"]

    # Chronological split, not random — never shuffle time series data,
    # or the model can "see" the future relative to the test window.
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
    print(f"[*] Out-of-sample R^2: {r2:.4f}")
    print("    (Daily returns are noisy — don't expect a high R^2. A small")
    print("     positive R^2 here means the model found *some* real signal;")
    print("     near-zero or negative means oil/rates barely explain gold's")
    print("     day-to-day moves, which is itself a useful finding.)")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)

    mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
    importance = pd.DataFrame({
        "factor": features,
        "mean_abs_shap_impact": mean_abs_shap,
    }).sort_values("mean_abs_shap_impact", ascending=False)

    print("\n=== Factor importance (mean |SHAP value|, higher = more explanatory) ===")
    print(importance.to_string(index=False))

    # Direction: for each factor, is its SHAP contribution positively or
    # negatively correlated with the feature's own value? (i.e. does high
    # oil_return push predicted gold_return up or down, on average)
    print("\n=== Direction check (correlation between feature value and its SHAP contribution) ===")
    direction_map = {}
    for i, feat in enumerate(features):
        corr = np.corrcoef(X_test[feat], shap_values.values[:, i])[0, 1]
        direction = "same direction (+)" if corr > 0 else "opposite direction (-)"
        direction_map[feat] = {"correlation": round(float(corr), 3), "direction": direction}
        print(f"    {feat}: corr={corr:.3f}  ->  {direction}")

    output_path = os.path.join(RESULT_DIR, "GOLD_PATTERNS_RESULT_10PCT.csv")
    importance.to_csv(output_path, index=False)
    print(f"\n[+] Factor importance saved: {output_path}")

    write_tier_summary(
        RESULT_DIR, "GOLD_10PCT", r2, len(X_train), len(X_test),
        df["date"].iloc[0], df["date"].iloc[-1], importance, direction_map,
    )

    return importance, r2


if __name__ == "__main__":
    run_patterns()
