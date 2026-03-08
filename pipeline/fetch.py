"""NOAA-002: NOAA CDO API client with caching, rate limiting, and retry."""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

NOAA_BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
RAW_DIR = Path("data/raw")


def _get_token() -> str:
    token = os.environ.get("NOAA_TOKEN", "")
    if not token:
        raise RuntimeError("NOAA_TOKEN not set. Get one at https://www.ncdc.noaa.gov/cdo-web/token")
    return token


def _cache_path(station_id: str, year: int) -> Path:
    safe_id = station_id.replace(":", "_")
    return RAW_DIR / f"{safe_id}_{year}.json"


def fetch_station_year(station_id: str, year: int, token: str = None) -> list:
    """Fetch GHCND daily data (TMAX, TMIN, PRCP) for one station and year.

    Returns list of observation dicts. Uses cache if available.
    """
    cache = _cache_path(station_id, year)
    if cache.exists() and cache.stat().st_size > 2:
        with open(cache) as f:
            return json.load(f)

    if token is None:
        token = _get_token()

    headers = {"token": token}
    all_results = []
    offset = 1

    while True:
        params = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "datatypeid": "TMAX,TMIN,PRCP",
            "startdate": f"{year}-01-01",
            "enddate": f"{year}-12-31",
            "units": "standard",  # we want raw metric; actually NOAA default is metric
            "limit": 1000,
            "offset": offset,
        }
        # Remove 'units' — we handle conversion ourselves from tenths-of-C
        del params["units"]

        resp = _request_with_retry(NOAA_BASE + "/data", params, headers)
        data = resp.json() if resp else {}
        results = data.get("results", [])
        all_results.extend(results)

        if len(results) < 1000:
            break
        offset += 1000
        time.sleep(0.2)

    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w") as f:
        json.dump(all_results, f)

    return all_results


def _request_with_retry(url: str, params: dict, headers: dict, retries: int = 3):
    """Make request with exponential backoff on 429/503."""
    for attempt in range(retries):
        time.sleep(0.2)  # rate limit: 5 req/sec
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code in (429, 503):
                wait = 2 ** (attempt + 1)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException:
            if attempt == retries - 1:
                return None
            time.sleep(2 ** (attempt + 1))
    return None


def fetch_region_data(station_ids: list, years: range, token: str = None) -> dict:
    """Fetch data for multiple stations and years. Returns {(station, year): [records]}."""
    if token is None:
        token = _get_token()

    result = {}
    for sid in station_ids:
        for year in years:
            records = fetch_station_year(sid, year, token)
            result[(sid, year)] = records
    return result
