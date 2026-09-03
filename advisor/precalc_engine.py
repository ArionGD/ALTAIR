import os
import sys
import time
import json
import threading
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf
from advisor.sectors import get_all_sectors, get_sector_tickers
from advisor.engine import run_advisor_scan

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
SNAPSHOT_FILE = os.path.join(SNAPSHOT_DIR, "orion_snapshots.json")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)

# IST Timezone (UTC +05:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30))

# User requested schedule: Mon, Tue, Wed, Thu, Fri at 9:00 AM, 11:55 AM, and 6:00 PM IST
SCHEDULE_SLOTS = ["09:00", "11:55", "18:00"]

# Global In-Memory Cache
_PRECALC_CACHE = {
    "metadata": {
        "last_sync_ist": None,
        "last_sync_slot": None,
        "next_sync_ist": None,
        "status": "initializing",
        "total_sectors": 0
    },
    "sectors": {}
}

_SCHEDULER_THREAD = None
_IS_CALCULATING = False


def get_current_ist() -> datetime:
    """Returns the current datetime in India Standard Time (IST)."""
    return datetime.now(IST_TZ)


def get_next_sync_slot() -> str:
    """Calculates the next upcoming scheduled sync slot in IST."""
    now = get_current_ist()
    weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    current_hm = now.strftime("%H:%M")

    # If today is a weekday, look for upcoming slots today
    if weekday < 5:
        for slot in SCHEDULE_SLOTS:
            if slot > current_hm:
                return f"Today ({now.strftime('%a')}) at {slot} IST"

    # Otherwise find the next weekday's first slot (09:00 AM)
    days_ahead = 1
    next_day = now + timedelta(days=days_ahead)
    while next_day.weekday() >= 5:  # Skip Saturday (5) and Sunday (6)
        days_ahead += 1
        next_day = now + timedelta(days=days_ahead)

    return f"{next_day.strftime('%A')} at 09:00 IST"


def load_snapshots_from_disk():
    """Loads pre-calculated snapshots from disk into memory if available."""
    global _PRECALC_CACHE
    if os.path.exists(SNAPSHOT_FILE):
        try:
            with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                _PRECALC_CACHE = data
                _PRECALC_CACHE["metadata"]["status"] = "ready"
                print(f"[ALTAIR PRECALC] Loaded {len(data.get('sectors', {}))} sector snapshots from disk.")
                return True
        except Exception as e:
            print(f"[ALTAIR PRECALC] Error reading snapshot file: {e}")
    return False


def save_snapshots_to_disk():
    """Atomically writes memory cache to disk snapshot file."""
    try:
        temp_file = SNAPSHOT_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(_PRECALC_CACHE, f, indent=2)
        if os.path.exists(SNAPSHOT_FILE):
            os.replace(temp_file, SNAPSHOT_FILE)
        else:
            os.rename(temp_file, SNAPSHOT_FILE)
    except Exception as e:
        print(f"[ALTAIR PRECALC] Error saving snapshots to disk: {e}")


def run_full_precalc_cycle(slot_name: str = "Manual / Startup"):
    """
    Executes the full batch calculation across all 10 NSE sectors.
    Computes DCF Intrinsic Values, Camarilla S1/R1 Brackets, Gann Scores, and Rankings.
    """
    global _PRECALC_CACHE, _IS_CALCULATING
    if _IS_CALCULATING:
        print("[ALTAIR PRECALC] Cycle already in progress, skipping concurrent call.")
        return

    _IS_CALCULATING = True
    start_time = time.time()
    now_ist = get_current_ist()
    print(f"\n=======================================================")
    print(f"[ALTAIR PRECALC] Starting Batch Cycle: {slot_name} at {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print(f"=======================================================")

    sectors = get_all_sectors()
    sector_results = {}

    for sec in sectors:
        try:
            print(f"[ALTAIR PRECALC] Pre-computing sector: {sec}...")
            # Compute default (include_gann=False)
            data_nogann = run_advisor_scan(sector_name=sec, include_gann=False)
            # Compute with Gann (include_gann=True)
            data_gann = run_advisor_scan(sector_name=sec, include_gann=True)

            sector_results[f"{sec}_nogann"] = data_nogann
            sector_results[f"{sec}_gann"] = data_gann
        except Exception as e:
            print(f"[ALTAIR PRECALC] Error calculating sector {sec}: {e}")

    elapsed = round(time.time() - start_time, 2)
    next_sync = get_next_sync_slot()

    _PRECALC_CACHE["metadata"] = {
        "last_sync_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "last_sync_slot": slot_name,
        "next_sync_ist": next_sync,
        "status": "ready",
        "total_sectors": len(sectors),
        "execution_seconds": elapsed,
        "schedule": ["09:00", "11:55", "18:00 (IST) Mon-Fri"]
    }
    _PRECALC_CACHE["sectors"] = sector_results

    save_snapshots_to_disk()
    _IS_CALCULATING = False
    print(f"[ALTAIR PRECALC] Cycle completed successfully in {elapsed}s. Next run: {next_sync}\n")


def get_precalculated_data(sector_name: str, include_gann: bool = False):
    """
    Returns precalculated sector data in under 2ms.
    Falls back to live calculation only if cache is completely empty.
    """
    cache_key = f"{sector_name}_gann" if include_gann else f"{sector_name}_nogann"
    
    # 1. Check in-memory
    if cache_key in _PRECALC_CACHE.get("sectors", {}):
        cached_data = _PRECALC_CACHE["sectors"][cache_key]
        return {
            "cached": True,
            "metadata": _PRECALC_CACHE.get("metadata", {}),
            "data": cached_data
        }

    # 2. Check disk if memory missed
    if load_snapshots_from_disk():
        if cache_key in _PRECALC_CACHE.get("sectors", {}):
            return {
                "cached": True,
                "metadata": _PRECALC_CACHE.get("metadata", {}),
                "data": _PRECALC_CACHE["sectors"][cache_key]
            }

    # 3. Fallback: Live run if not in cache yet
    print(f"[ALTAIR PRECALC] Cache miss for {sector_name}, running on-demand scan...")
    live_data = run_advisor_scan(sector_name=sector_name, include_gann=include_gann)
    return {
        "cached": False,
        "metadata": {
            "last_sync_ist": "On-demand execution",
            "next_sync_ist": get_next_sync_slot()
        },
        "data": live_data
    }


def _scheduler_loop():
    """
    Background worker thread monitoring India Standard Time.
    Triggers automatically on Monday-Friday at 09:00, 11:55, and 18:00 IST.
    """
    last_triggered_slot = None

    while True:
        try:
            now_ist = get_current_ist()
            weekday = now_ist.weekday()  # 0=Monday, 4=Friday
            current_hm = now_ist.strftime("%H:%M")
            slot_id = f"{now_ist.strftime('%Y-%m-%d')}_{current_hm}"

            # Only run on working days (Mon-Fri)
            if weekday < 5 and current_hm in SCHEDULE_SLOTS:
                if last_triggered_slot != slot_id:
                    last_triggered_slot = slot_id
                    slot_label = f"Scheduled {current_hm} IST"
                    run_full_precalc_cycle(slot_name=slot_label)

            time.sleep(20)  # Check every 20 seconds
        except Exception as e:
            print(f"[ALTAIR PRECALC SCHEDULER] Exception in scheduler loop: {e}")
            time.sleep(30)


def start_precalc_scheduler():
    """Initializes the background scheduler and loads/warms snapshots."""
    global _SCHEDULER_THREAD
    # First attempt to load existing snapshot from disk
    has_snapshots = load_snapshots_from_disk()

    # Start the daemon scheduler thread
    if _SCHEDULER_THREAD is None or not _SCHEDULER_THREAD.is_alive():
        _SCHEDULER_THREAD = threading.Thread(target=_scheduler_loop, daemon=True, name="OrionPrecalcScheduler")
        _SCHEDULER_THREAD.start()
        print(f"[ALTAIR PRECALC] Background scheduler active. Slots: {SCHEDULE_SLOTS} IST (Mon-Fri).")

    # If no snapshot exists on disk, warm up the cache asynchronously
    if not has_snapshots:
        print("[ALTAIR PRECALC] No existing snapshots found. Triggering initial warm-up in background...")
        warmup_thread = threading.Thread(target=run_full_precalc_cycle, args=("Initial Startup Warm-Up",), daemon=True)
        warmup_thread.start()
