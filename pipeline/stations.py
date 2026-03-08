"""NOAA-001: Station discovery — find best GHCND stations for each AVA region."""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .regions import REGIONS, AVARegion

load_dotenv()

NOAA_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
STATIONS_CACHE = Path("data/processed/stations.json")


def _get_token() -> str:
    token = os.environ.get("NOAA_TOKEN", "")
    return token


def discover_stations_for_region(region: AVARegion, token: str) -> list:
    """Query NOAA API to find GHCND stations near a region's coordinates."""
    url = f"{NOAA_BASE}/stations"
    params = {
        "datasetid": "GHCND",
        "datatypeid": "TMAX,TMIN",
        "extent": f"{region.lat - 0.3},{region.lon - 0.3},{region.lat + 0.3},{region.lon + 0.3}",
        "limit": 10,
        "sortfield": "datacoverage",
        "sortorder": "desc",
    }
    headers = {"token": token}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return [s["id"] for s in results if s.get("datacoverage", 0) > 0.8][:3]
    except Exception:
        return []


def get_station_mapping(force_refresh: bool = False) -> dict:
    """Return dict of region_name -> list of station IDs.

    Uses cached file if available. Falls back to hardcoded stations if no token.
    """
    if STATIONS_CACHE.exists() and not force_refresh:
        with open(STATIONS_CACHE) as f:
            return json.load(f)

    token = _get_token()
    mapping = {}

    for region in REGIONS:
        stations = []
        if token:
            stations = discover_stations_for_region(region, token)
            time.sleep(0.2)  # rate limit
        if not stations:
            stations = list(region.fallback_stations)
        mapping[region.name] = stations

    STATIONS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATIONS_CACHE, "w") as f:
        json.dump(mapping, f, indent=2)

    return mapping


if __name__ == "__main__":
    mapping = get_station_mapping()
    for name, sids in mapping.items():
        print(f"{name}: {sids}")
