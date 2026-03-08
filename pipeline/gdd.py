"""NOAA-003: GDD calculation using the Winkler method."""

import pandas as pd
import numpy as np
from typing import Optional


# Winkler region classification
WINKLER_REGIONS = [
    (2500, "I"),
    (3000, "II"),
    (3500, "III"),
    (4000, "IV"),
    (float("inf"), "V"),
]


def classify_winkler(gdd: float) -> str:
    """Classify cumulative GDD into Winkler region I-V."""
    for threshold, label in WINKLER_REGIONS:
        if gdd < threshold:
            return label
    return "V"


def parse_noaa_records(records: list) -> pd.DataFrame:
    """Parse NOAA GHCND records into a daily DataFrame with TMAX, TMIN, PRCP columns.

    NOAA stores TMAX/TMIN in tenths of degrees Celsius.
    """
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.date

    # Pivot so each datatype is a column
    pivot = df.pivot_table(index="date", columns="datatype", values="value", aggfunc="first")
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.sort_index()
    return pivot


def compute_daily_gdd(daily_df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Compute daily GDD for the growing season (Apr 1 – Oct 31).

    Expects DataFrame with TMAX, TMIN columns (tenths of degrees Celsius).
    Returns DataFrame with date, tmax_f, tmin_f, daily_gdd, cumulative_gdd.
    """
    start = pd.Timestamp(year, 4, 1)
    end = pd.Timestamp(year, 10, 31)

    # Create full date range for the season
    full_range = pd.date_range(start, end, freq="D")
    season = daily_df.reindex(full_range)

    result = pd.DataFrame(index=full_range)
    result.index.name = "date"

    # Convert tenths-of-Celsius to Fahrenheit
    if "TMAX" in season.columns:
        result["tmax_f"] = season["TMAX"] / 10.0 * 9.0 / 5.0 + 32.0
    else:
        result["tmax_f"] = np.nan

    if "TMIN" in season.columns:
        result["tmin_f"] = season["TMIN"] / 10.0 * 9.0 / 5.0 + 32.0
    else:
        result["tmin_f"] = np.nan

    # Interpolate gaps <= 3 days
    result["tmax_f"] = result["tmax_f"].interpolate(method="linear", limit=3)
    result["tmin_f"] = result["tmin_f"].interpolate(method="linear", limit=3)

    # Flag gaps > 3 days (still NaN after interpolation)
    result["gap_flag"] = result["tmax_f"].isna() | result["tmin_f"].isna()

    # Daily GDD
    result["daily_gdd"] = np.maximum(0, (result["tmax_f"] + result["tmin_f"]) / 2.0 - 50.0)
    result["daily_gdd"] = result["daily_gdd"].fillna(0)

    # Cumulative GDD (Winkler Index when complete)
    result["cumulative_gdd"] = result["daily_gdd"].cumsum()

    return result


def compute_winkler_index(daily_df: pd.DataFrame, year: int) -> dict:
    """Compute the Winkler Index and classification for a station-year."""
    gdd_df = compute_daily_gdd(daily_df, year)
    winkler_gdd = gdd_df["cumulative_gdd"].iloc[-1] if len(gdd_df) > 0 else 0.0
    gap_days = int(gdd_df["gap_flag"].sum()) if len(gdd_df) > 0 else 214
    return {
        "year": year,
        "winkler_gdd": round(winkler_gdd, 1),
        "winkler_region": classify_winkler(winkler_gdd),
        "gap_days": gap_days,
        "daily_gdd": gdd_df,
    }


def compute_historical_mean(results: list, baseline_start: int = 2000, baseline_end: int = 2022) -> float:
    """Compute mean Winkler GDD over a baseline period."""
    baseline = [r["winkler_gdd"] for r in results if baseline_start <= r["year"] <= baseline_end]
    return round(np.mean(baseline), 1) if baseline else 0.0
