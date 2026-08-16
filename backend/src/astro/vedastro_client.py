import requests
import time
import logging
import json
import os
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VedAstroClient")

BASE_URL = "https://api.vedastro.org/api/Calculate"
API_KEY = "FreeAPIUser"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "astro_cache.json")

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"natal": {}, "transits": {}}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving cache: {e}")

def call_vedastro_api(endpoint, params, retries=3, delay=2):
    url = f"{BASE_URL}/{endpoint}"
    payload = dict(params)
    payload["APIKey"] = API_KEY
    
    for attempt in range(retries):
        try:
            r = requests.post(url, json=payload, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("Status") == "Fail":
                    logger.warning(f"VedAstro API Fail: {data.get('Payload', 'Unknown')}")
                    return None
                
                payload_data = data.get("Payload", {})
                if isinstance(payload_data, dict):
                    vals = list(payload_data.values())
                    return vals[0] if len(vals) == 1 else payload_data
                return payload_data
            else:
                logger.warning(f"HTTP Error {r.status_code} calling {endpoint}")
        except Exception as e:
            logger.warning(f"Error calling {endpoint} (Attempt {attempt+1}/{retries}): {e}")
            
        time.sleep(delay)
    return None

def fetch_company_astrology(ticker, birth_date_str, birth_time_str, timezone_str, latitude, longitude, city_name, current_time_str=None):
    """
    Fetches the company natal chart, current Dasha, and transits, using a local file-based cache.
    """
    ticker = ticker.upper()
    cache = load_cache()
    
    # Check if we have cached natal data
    natal_data = cache["natal"].get(ticker)
    
    # Format times for API
    dt_parts = birth_date_str.split("-")
    day = dt_parts[2]
    month = dt_parts[1]
    year = dt_parts[0]
    
    formatted_birth_time = f"{birth_time_str} {day}/{month}/{year} {timezone_str}"
    
    geo = {
        "Name": city_name,
        "Longitude": float(longitude),
        "Latitude": float(latitude)
    }
    
    birth_time_payload = {
        "StdTime": formatted_birth_time,
        "Location": geo
    }
    
    # Calculate current date string for transit cache
    if not current_time_str:
        now = datetime.datetime.now(datetime.timezone.utc)
        current_time_str = now.strftime("%H:%M %d/%m/%Y +00:00")
        today_str = now.strftime("%Y-%m-%d")
    else:
        # Custom time string format expected: e.g. "19:30 11/06/2026 +05:30"
        try:
            # Try parsing date parts
            time_parts = current_time_str.split(" ")
            date_parts = time_parts[1].split("/")
            today_str = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
        except Exception:
            today_str = "custom-date"
            
    current_time_payload = {
        "StdTime": current_time_str,
        "Location": {
            "Name": "Current Observation Point",
            "Longitude": 0.0,
            "Latitude": 51.47
        }
    }
    
    # Initialize cache structures if not present
    if "natal" not in cache:
        cache["natal"] = {}
    if "transits" not in cache:
        cache["transits"] = {}
    if today_str not in cache["transits"]:
        cache["transits"][today_str] = {}
        
    transit_cached = cache["transits"][today_str].get(ticker)
    
    # Step 1: Resolve Natal Data (API or Cache)
    if not natal_data:
        logger.info(f"Cache miss for {ticker} natal data. Calling VedAstro API...")
        results = {}
        
        # Lagna
        results["Lagna"] = call_vedastro_api("LagnaSignName", {"time": birth_time_payload})
        time.sleep(0.3)
        
        # Moon Nakshatra
        results["MoonNakshatra"] = call_vedastro_api("MoonConstellation", {"time": birth_time_payload})
        time.sleep(0.3)
        
        # Natal Planets
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        natal_planets = {}
        for p in planets:
            res = call_vedastro_api("PlanetRasiD1Sign", {"planetName": {"Name": p}, "time": birth_time_payload})
            if isinstance(res, dict):
                natal_planets[p] = res.get("Name", "?")
            else:
                natal_planets[p] = res
            time.sleep(0.2)
        results["NatalPlanets"] = natal_planets
        
        # House Signs
        house_signs = {}
        for i in range(1, 13):
            res = call_vedastro_api("HouseSignName", {"houseNumber": f"House{i}", "time": birth_time_payload})
            if isinstance(res, dict):
                house_signs[f"House_{i}"] = res.get("Name", "?")
            else:
                house_signs[f"House_{i}"] = res
            time.sleep(0.2)
        results["HouseSigns"] = house_signs
        
        # Save to cache
        cache["natal"][ticker] = results
        save_cache(cache)
        natal_data = results
    else:
        logger.info(f"Cache hit for {ticker} natal data.")
        
    # Step 2: Resolve Transit and Dasha Data (API or Cache)
    if not transit_cached:
        logger.info(f"Cache miss for {ticker} transits on {today_str}. Calling VedAstro API...")
        results = {}
        
        # Current Dasha
        dasha_res = call_vedastro_api("DasaAtTime", {"birthTime": birth_time_payload, "checkTime": current_time_payload})
        active_mahadasha = "Unknown"
        active_bhukti = "Unknown"
        if dasha_res and isinstance(dasha_res, dict):
            mahadashas = list(dasha_res.keys())
            if mahadashas:
                active_mahadasha = mahadashas[0]
                subdasas = dasha_res[active_mahadasha].get("SubDasas", {})
                if subdasas:
                    active_bhukti = list(subdasas.keys())[0]
                    
        results["CurrentDasha"] = {
            "Mahadasha": active_mahadasha,
            "Bhukti": active_bhukti
        }
        time.sleep(0.3)
        
        # Current Transits
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        transit_planets = {}
        for p in planets:
            res = call_vedastro_api("PlanetRasiD1Sign", {"planetName": {"Name": p}, "time": current_time_payload})
            if isinstance(res, dict):
                transit_planets[p] = res.get("Name", "?")
            else:
                transit_planets[p] = res
            time.sleep(0.2)
        results["Transits"] = transit_planets
        
        # Save to cache
        cache["transits"][today_str][ticker] = results
        save_cache(cache)
        transit_cached = results
    else:
        logger.info(f"Cache hit for {ticker} transits on {today_str}.")
        
    # Combine natal and transit data for return
    combined = dict(natal_data)
    combined.update(transit_cached)
    return combined

if __name__ == "__main__":
    # Test call
    res = fetch_company_astrology("AAPL", "1977-01-03", "09:00", "-08:00", 37.323, -122.032, "Cupertino, CA, USA")
    print(res)
