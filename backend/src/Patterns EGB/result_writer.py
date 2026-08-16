"""
Shared helper for writing a standard per-tier EGB result summary — used by
every run_gold_patterns*.py script so the dashboard's EGB GlassBox tab has
one consistent schema to read across tiers, regardless of how many
factors a given tier adds.
"""
import json
import os


def write_tier_summary(output_dir, tier_name, r2, n_train, n_test,
                        date_start, date_end, importance_df, direction_map):
    """Writes {tier_name}_SUMMARY.json — the file the dashboard reads.

    importance_df: DataFrame with columns [factor, mean_abs_shap_impact],
    already sorted descending.
    direction_map: {factor: {"correlation": float, "direction": str}}
    """
    factors = []
    for _, row in importance_df.iterrows():
        factor = row["factor"]
        dir_info = direction_map.get(factor, {})
        factors.append({
            "factor": factor,
            "mean_abs_shap_impact": float(row["mean_abs_shap_impact"]),
            "correlation": dir_info.get("correlation"),
            "direction": dir_info.get("direction"),
        })

    summary = {
        "tier": tier_name,
        "r2": round(float(r2), 4),
        "n_train": int(n_train),
        "n_test": int(n_test),
        "date_start": str(date_start),
        "date_end": str(date_end),
        "factors": factors,
    }

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{tier_name}_SUMMARY.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[+] Tier summary saved: {path}")
    return path
