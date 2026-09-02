import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'sectors.json')

with open(JSON_PATH, 'r', encoding='utf-8') as f:
    SECTORS_MAP = json.load(f)

def get_sector_tickers(sector_name: str) -> list:
    return SECTORS_MAP.get(sector_name, SECTORS_MAP['Pharma & Healthcare'])

def get_all_sectors() -> list:
    return list(SECTORS_MAP.keys())
