"""NOAA-004: Frost date detection — last spring frost, first fall frost."""

import pandas as pd
import numpy as np


def detect_frost_dates(daily_df: pd.DataFrame, year: int) -> dict:
    """Detect last spring frost and first fall frost for a given year.

    Expects DataFrame with TMIN column in tenths of degrees Celsius.
    """
    if daily_df.empty or "TMIN" not in daily_df.columns:
        return {
            "year": year,
            "last_spring_frost": None,
            "first_fall_frost": None,
            "frost_free_days": None,
            "no_frost_flag": True,
        }

    # Convert TMIN to Fahrenheit
    df = daily_df.copy()
    df["tmin_f"] = df["TMIN"] / 10.0 * 9.0 / 5.0 + 32.0

    # Last spring frost: latest day in Jan-Jun with TMIN <= 32°F
    spring = df.loc[
        (df.index >= pd.Timestamp(year, 1, 1)) & (df.index <= pd.Timestamp(year, 6, 30))
    ]
    spring_frost = spring[spring["tmin_f"] <= 32.0]
    last_spring = spring_frost.index.max() if len(spring_frost) > 0 else None

    # First fall frost: earliest day in Aug-Dec with TMIN <= 32°F
    fall = df.loc[
        (df.index >= pd.Timestamp(year, 8, 1)) & (df.index <= pd.Timestamp(year, 12, 31))
    ]
    fall_frost = fall[fall["tmin_f"] <= 32.0]
    first_fall = fall_frost.index.min() if len(fall_frost) > 0 else None

    # Frost-free days
    frost_free = None
    if last_spring is not None and first_fall is not None:
        frost_free = (first_fall - last_spring).days

    return {
        "year": year,
        "last_spring_frost": last_spring.strftime("%Y-%m-%d") if last_spring else None,
        "first_fall_frost": first_fall.strftime("%Y-%m-%d") if first_fall else None,
        "frost_free_days": frost_free,
        "no_frost_flag": last_spring is None and first_fall is None,
    }


def compute_historical_frost_averages(frost_results: list) -> dict:
    """Compute average frost dates over the baseline period."""
    spring_doys = []
    fall_doys = []
    ff_days = []
    for r in frost_results:
        if r["last_spring_frost"]:
            d = pd.Timestamp(r["last_spring_frost"])
            spring_doys.append(d.dayofyear)
        if r["first_fall_frost"]:
            d = pd.Timestamp(r["first_fall_frost"])
            fall_doys.append(d.dayofyear)
        if r["frost_free_days"] is not None:
            ff_days.append(r["frost_free_days"])

    return {
        "avg_last_spring_frost_doy": round(np.mean(spring_doys)) if spring_doys else None,
        "avg_first_fall_frost_doy": round(np.mean(fall_doys)) if fall_doys else None,
        "avg_frost_free_days": round(np.mean(ff_days)) if ff_days else None,
    }
