# 🏛️ ALTAIR: Interpretation Protocol & Agent Guide

This document serves as the primary guidance for any AI Agent or Analyst interacting with the ALTAIR Base engine. It ensures consistent interpretation of the "Sovereign Predation" metrics.

---

## 🎯 1. The Prime Objective
ALTAIR's goal is **not** to find "value" or "growth." Its goal is to find **Structural Fragility**. 
> [!IMPORTANT]
> A High Score in ALTAIR = A Weak Company. 
> A Low Score in ALTAIR = A Strong/Protected Company.

---

## 📊 2. The "Sovereign Six" Metric Matrix (V5.0)

| Metric | Range | Logic | High Score (>70) | Low Score (<30) |
| :--- | :--- | :--- | :--- | :--- |
| **AVS Score** | 1-100 | **Fragility Index** | **Target**: Structurally weak | **Avoid**: Iron Fortress |
| **Z-Score** | <5 | **Solvency Risk** | **Distress**: Score < 1.8 | **Healthy**: Score > 3.0 |
| **PR Score** | 1-100 | **Pledge Rate** | **Margin Call**: Founder Debt | **Safe**: No pledging |
| **Sentiment**| 1-100 | **News Decay** | **Fear**: High news pressure | **Hype**: Positive/Neutral |
| **Bailout %** | 0-100 | **Sovereign Shield** | **Invincible**: Core PSU/Bank | **Sacrifice**: Tech/Retail |
| **SS Score %**| 1-100 | **Strike Priority** | **EXECUTE**: Ready for Strike | **HOLD**: Not yet ripe |

---

## 🎯 3. The V5.0 Weighting Engine
The ALTAIR AVS V5.0 (Sovereign Strike Tier) integrates all factors:
- **30% Fundamentals**: (PE + Debt/Equity).
- **25% Solvency**: (Z-Score < 1.8).
- **20% Pledge Rate (PR)**: Founder leverage risk.
- **15% Sentiment**: News-based fear scavenging.
- **10% VIX Beta**: Panic sensitivity.
- **Bailout Modifier**: Reduces SS Score (Sovereign Shield).

---

## 🏹 4. The "Tiger-Strike" Protocol

When an agent is asked to "Identify Targets," they must follow this specific analytical sequence:

### Step 1: fundamental Heat (AVS)
Check the `avs_score` (VulnerabilityRanker). If AVS > 70, the company has "Air and Weight" (High PE + High Debt).

### Step 2: Solvency Check (Z-Score)
Validate the AVS with `z_score` (ZScoreEngine).
- **Z < 1.8**: The company is mathematically likely to fail during a liquidity crunch.
- **Z > 3.0**: Even if the PE is high, the company is solvent. *Caution recommended for shorting.*

### Step 3: Sovereign Floor (Bailout)
Check `bailout_probability` (BailoutAuditor). 
- **DO NOT SHORT** companies with Bailout > 80% (e.g., Banks, Defense, Core PSU).
- **PRIORITIZE** companies with Bailout < 10% (e.g., Loss-making consumer tech).

### Step 4: The Kill Zone (SS Score)
Combine the above into the `astra_strike_score`. This is the final priority list.
- **SS > 85**: "The Glass Pillar." These are the primary targets for the April 19, 2026 Window.

---

## 🏛️ 4. Sovereign Context (The "Orion" Link)
Always remember: **ALTAIR identifies the TARGET, but ORION identifies the TIMING.**
- Do not execute strikes based on ALTAIR scores alone if the **Astro Pulse** (Fracture Risk) is not "CRITICAL."
- Monitor `get_astro_pulse()` for the countdown to the April 19, 2026 Fracture.

---

## 🛡️ Agent Note on Source Data
ALTAIR relies on `yfinance`. If the `z_score` returns "Incomplete Data," the agent should perform a manual audit of the `Current Assets` and `Total Liabilities` before assigning a final vulnerability rating.
