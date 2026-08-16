import os
import pandas as pd
import logging
from src.astro.vedastro_client import fetch_company_astrology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AlphaAnalyzer")

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "company_natal_registry.csv")
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
STRIKE_MAP_PATH = os.path.join(BASE_DIR, "database", "processed", "GLOBAL_STRIKE_MAP_2026.csv")

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_LORDS = {
    "Aries": "Mars", "Scorpio": "Mars",
    "Taurus": "Venus", "Libra": "Venus",
    "Gemini": "Mercury", "Virgo": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Sagittarius": "Jupiter", "Pisces": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Saturn"
}

def get_sign_index(sign_name):
    try:
        return ZODIAC_SIGNS.index(sign_name) + 1
    except ValueError:
        return 1

def calculate_house_of_sign(lagna_sign, target_sign):
    """Calculates the house number (1-12) of a target zodiac sign relative to the Lagna sign."""
    lagna_idx = get_sign_index(lagna_sign)
    target_idx = get_sign_index(target_sign)
    house = target_idx - lagna_idx + 1
    if house <= 0:
        house += 12
    return house

def get_financial_data(ticker):
    """Loads fundamental metrics for a given ticker from the GLOBAL_STRIKE_MAP_2026.csv file."""
    if not os.path.exists(STRIKE_MAP_PATH):
        logger.warning(f"Strike map not found at {STRIKE_MAP_PATH}. Using fallback financial metrics.")
        return None
        
    try:
        df = pd.read_csv(STRIKE_MAP_PATH)
        row = df[df["ticker"].str.upper() == ticker.upper()]
        if not row.empty:
            return row.iloc[0].to_dict()
    except Exception as e:
        logger.error(f"Error reading financial data: {e}")
    return None

def analyze_company_alpha(ticker, current_time_str=None):
    """
    Combines the company's astrological metadata with financial metrics to generate a Unified Alpha call.
    """
    # 1. Load company natal registration details
    if not os.path.exists(REGISTRY_PATH):
        return {"status": "error", "message": "Company registry file not found."}
        
    df_reg = pd.read_csv(REGISTRY_PATH)
    company_row = df_reg[df_reg["ticker"].str.upper() == ticker.upper()]
    
    if company_row.empty:
        return {"status": "error", "message": f"Ticker {ticker} not found in corporate natal registry."}
        
    co_data = company_row.iloc[0]
    
    # 2. Fetch astrological coordinates from VedAstro API
    astro_data = fetch_company_astrology(
        ticker=ticker,
        birth_date_str=co_data["incorporation_date"],
        birth_time_str=co_data["incorporation_time"],
        timezone_str=co_data["timezone"],
        latitude=co_data["latitude"],
        longitude=co_data["longitude"],
        city_name=f"{co_data['city']}, {co_data['state']}, {co_data['country']}",
        current_time_str=current_time_str
    )
    
    if not astro_data or "Lagna" not in astro_data:
        return {"status": "error", "message": "Failed to retrieve data from VedAstro API."}
        
    # 3. Load financial data
    fin_data = get_financial_data(ticker)
    avs_score = 50.0 # Default fallback
    pe_ratio = 0.0
    if fin_data:
        avs_score = fin_data.get("avs_score", 50.0)
        pe_ratio = fin_data.get("pe_ratio", 0.0)
    
    # Financial quality score (low fragility = high quality)
    financial_quality = round(100.0 - avs_score, 2)
    
    # 4. Run Astrological Scoring logic
    lagna = astro_data["Lagna"]
    moon_sign = astro_data["NatalPlanets"].get("Moon", "?")
    
    # A. Dasha Strength (40 points max)
    dasha = astro_data["CurrentDasha"]
    mahadasha = dasha.get("Mahadasha", "Unknown")
    bhukti = dasha.get("Bhukti", "Unknown")
    
    dasha_score = 15 # Default/Neutral
    benefics = ["Jupiter", "Venus", "Mercury", "Moon"]
    malefics = ["Saturn", "Mars", "Rahu", "Ketu", "Sun"]
    
    if mahadasha in benefics:
        dasha_score = 30
        if bhukti in benefics:
            dasha_score = 40
    elif mahadasha in malefics:
        dasha_score = 10
        if bhukti in malefics:
            dasha_score = 5
            
    # B. Transit Strength (30 points max)
    transits = astro_data["Transits"]
    tr_jupiter = transits.get("Jupiter", "?")
    tr_venus = transits.get("Venus", "?")
    tr_saturn = transits.get("Saturn", "?")
    
    transit_score = 15 # Default
    # Benefic transit houses: 2nd (wealth), 5th (speculation), 9th (luck), 10th (status), 11th (gains)
    jup_house = calculate_house_of_sign(lagna, tr_jupiter)
    ven_house = calculate_house_of_sign(lagna, tr_venus)
    sat_house = calculate_house_of_sign(lagna, tr_saturn)
    
    favorable_houses = [2, 5, 9, 10, 11]
    if jup_house in favorable_houses:
        transit_score += 10
    if ven_house in favorable_houses:
        transit_score += 5
        
    # Saturn in 8th/12th (heavy pressure) or Sade Sati (Saturn transiting 12th, 1st, 2nd from Natal Moon)
    sat_moon_house = calculate_house_of_sign(moon_sign, tr_saturn)
    if sat_house in [8, 12] or sat_moon_house in [12, 1, 2]:
        transit_score = max(0, transit_score - 10)
        
    # C. Natal Yoga Placements (30 points max)
    natal_score = 15 # Default
    nat_jup = astro_data["NatalPlanets"].get("Jupiter", "?")
    nat_ven = astro_data["NatalPlanets"].get("Venus", "?")
    
    jup_natal_house = calculate_house_of_sign(lagna, nat_jup)
    ven_natal_house = calculate_house_of_sign(lagna, nat_ven)
    
    # Jupiter/Venus in Kendra (1, 4, 7, 10) or Trikona (5, 9) or 11th
    if jup_natal_house in [1, 4, 5, 7, 9, 10, 11]:
        natal_score += 10
    if ven_natal_house in [1, 4, 5, 7, 9, 10, 11]:
        natal_score += 5
        
    # Lagna Lord strength
    lagna_lord = SIGN_LORDS.get(lagna, "Sun")
    if lagna_lord in benefics:
        natal_score = min(30, natal_score + 5)
        
    astro_growth_score = round(dasha_score + transit_score + natal_score, 2)
    
    # 5. Compile Unified Alpha Score (50% Financial Quality, 50% Astro Timing)
    unified_alpha_score = round((financial_quality * 0.5) + (astro_growth_score * 0.5), 2)
    
    # 6. Generate Interpreted calls
    call_recommendation = "HOLD (Neutral)"
    call_color = "gray"
    call_description = "The stock exhibits stable fundamentals with standard astronomical configurations. Monitor transit changes."
    
    if financial_quality >= 60.0 and astro_growth_score >= 65.0:
        call_recommendation = "STRONG BUY (Alpha Synergy)"
        call_color = "green"
        call_description = "Excellent fundamental strength combined with a powerful astrological dasha and transit alignment. High probability of substantial capital appreciation."
    elif financial_quality < 45.0 and astro_growth_score < 45.0:
        call_recommendation = "SOVEREIGN SHORT (Structural Fracture)"
        call_color = "red"
        call_description = "Severe financial fragility combined with a challenging malefic dasha/transit (e.g. Sade Sati or Saturn hits). High risk of collapse or sharp downward correction."
    elif financial_quality >= 55.0 and astro_growth_score < 45.0:
        call_recommendation = "OPERATIONAL HOLD (Astro Transition)"
        call_color = "yellow"
        call_description = "Strong balance sheet and operations, but currently undergoing an operational restructuring or consolidation phase due to heavy planetary aspects (e.g., Saturn transit). Avoid new buying, hold existing shares."
    elif financial_quality < 45.0 and astro_growth_score >= 65.0:
        call_recommendation = "SPECULATIVE PLAY (Astro Tailwind)"
        call_color = "indigo"
        call_description = "Weak fundamentals, but experiencing temporary explosive momentum driven by disruptive Rahu transits or sudden dasha changes. Suitable for high-risk speculative trading only, not long-term holdings."
        
    return {
        "ticker": ticker,
        "company_name": co_data["company_name"],
        "incorporation_date": co_data["incorporation_date"],
        "city": co_data["city"],
        "country": co_data["country"],
        "financial_quality": financial_quality,
        "avs_score": avs_score,
        "pe_ratio": pe_ratio,
        "lagna": lagna,
        "moon_nakshatra": astro_data["MoonNakshatra"],
        "current_mahadasha": mahadasha,
        "current_bhukti": bhukti,
        "astro_growth_score": astro_growth_score,
        "unified_alpha_score": unified_alpha_score,
        "call_recommendation": call_recommendation,
        "call_color": call_color,
        "call_description": call_description,
        "details": {
            "dasha_score": dasha_score,
            "transit_score": transit_score,
            "natal_score": natal_score,
            "jup_house": jup_house,
            "ven_house": ven_house,
            "sat_house": sat_house,
            "sat_moon_house": sat_moon_house,
            "jup_natal_house": jup_natal_house,
            "ven_natal_house": ven_natal_house
        }
    }

if __name__ == "__main__":
    import json
    # Quick debug run
    res = analyze_company_alpha("RELIANCE.NS")
    print(json.dumps(res, indent=2))
