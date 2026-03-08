"""NOAA-001: AVA region definitions with coordinates and representative zip codes."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class AVARegion:
    name: str
    state: str
    zip_code: str
    lat: float
    lon: float
    key_varieties: List[str] = field(default_factory=list)
    fallback_stations: List[str] = field(default_factory=list)


REGIONS = [
    AVARegion(
        name="Napa Valley", state="CA", zip_code="94558",
        lat=38.50, lon=-122.27,
        key_varieties=["Cabernet Sauvignon", "Chardonnay"],
        fallback_stations=["GHCND:USC00046826"],
    ),
    AVARegion(
        name="Sonoma County", state="CA", zip_code="95476",
        lat=38.29, lon=-122.46,
        key_varieties=["Pinot Noir", "Zinfandel", "Chardonnay"],
        fallback_stations=["GHCND:USC00048351"],
    ),
    AVARegion(
        name="Russian River Valley", state="CA", zip_code="95403",
        lat=38.51, lon=-122.79,
        key_varieties=["Pinot Noir", "Chardonnay"],
        fallback_stations=["GHCND:USC00047769"],
    ),
    AVARegion(
        name="Paso Robles", state="CA", zip_code="93446",
        lat=35.63, lon=-120.69,
        key_varieties=["Cabernet", "Zinfandel", "Rhône varieties"],
        fallback_stations=["GHCND:USC00046730"],
    ),
    AVARegion(
        name="Central Coast", state="CA", zip_code="93401",
        lat=35.28, lon=-120.66,
        key_varieties=["Chardonnay", "Pinot Noir"],
        fallback_stations=["GHCND:USC00047851"],
    ),
    AVARegion(
        name="Mendocino", state="CA", zip_code="95460",
        lat=39.15, lon=-123.21,
        key_varieties=["Zinfandel", "Pinot Noir"],
        fallback_stations=["GHCND:USC00045360"],
    ),
    AVARegion(
        name="Willamette Valley", state="OR", zip_code="97128",
        lat=45.21, lon=-123.19,
        key_varieties=["Pinot Noir", "Pinot Gris"],
        fallback_stations=["GHCND:USC00354835"],
    ),
    AVARegion(
        name="Columbia Valley", state="WA", zip_code="99301",
        lat=46.21, lon=-119.17,
        key_varieties=["Cabernet", "Riesling", "Chardonnay"],
        fallback_stations=["GHCND:USC00454528"],
    ),
    AVARegion(
        name="Walla Walla", state="WA", zip_code="99362",
        lat=46.07, lon=-118.33,
        key_varieties=["Cabernet", "Syrah", "Merlot"],
        fallback_stations=["GHCND:USC00458773"],
    ),
    AVARegion(
        name="Finger Lakes", state="NY", zip_code="14456",
        lat=42.87, lon=-77.01,
        key_varieties=["Riesling", "Gewürztraminer"],
        fallback_stations=["GHCND:USC00303026"],
    ),
    AVARegion(
        name="Lodi", state="CA", zip_code="95240",
        lat=38.13, lon=-121.27,
        key_varieties=["Zinfandel", "Cabernet"],
        fallback_stations=["GHCND:USC00044500"],
    ),
    AVARegion(
        name="Alexander Valley", state="CA", zip_code="95448",
        lat=38.81, lon=-122.99,
        key_varieties=["Cabernet Sauvignon"],
        fallback_stations=["GHCND:USC00041715"],
    ),
]

REGION_MAP = {r.name: r for r in REGIONS}


def get_region(name: str) -> AVARegion:
    """Get region by name."""
    return REGION_MAP[name]


def get_all_regions() -> list:
    """Return all defined AVA regions."""
    return list(REGIONS)
