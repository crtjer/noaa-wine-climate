"""NOAA-005 (part 1): Full metrics computation — combines GDD, frost, and derived scores.

Usage:
    python -m pipeline.metrics              # Full run (requires NOAA_TOKEN)
    python -m pipeline.metrics --demo       # Demo mode with synthetic data
"""

import argparse
import sys

import numpy as np
import pandas as pd

from .gdd import parse_noaa_records, compute_daily_gdd, compute_winkler_index, classify_winkler, compute_historical_mean
from .frost import detect_frost_dates, compute_historical_frost_averages
from .export import (
    write_by_region_year,
    write_winkler_heatmap,
    write_gdd_timeseries,
    write_vintage_signals,
    write_summary_json,
)
from .regions import REGIONS, REGION_MAP


def compute_heat_events(daily_df: pd.DataFrame, year: int, threshold_f: float = 95.0) -> int:
    """Count days with TMAX > threshold during growing season (Apr-Oct)."""
    if daily_df.empty or "TMAX" not in daily_df.columns:
        return 0
    start = pd.Timestamp(year, 4, 1)
    end = pd.Timestamp(year, 10, 31)
    season = daily_df.loc[(daily_df.index >= start) & (daily_df.index <= end)]
    if season.empty:
        return 0
    tmax_f = season["TMAX"] / 10.0 * 9.0 / 5.0 + 32.0
    return int((tmax_f > threshold_f).sum())


def compute_season_precip(daily_df: pd.DataFrame, year: int) -> float:
    """Total precipitation (mm) during growing season Apr-Oct. PRCP is in tenths of mm."""
    if daily_df.empty or "PRCP" not in daily_df.columns:
        return 0.0
    start = pd.Timestamp(year, 4, 1)
    end = pd.Timestamp(year, 10, 31)
    season = daily_df.loc[(daily_df.index >= start) & (daily_df.index <= end)]
    if season.empty:
        return 0.0
    return round(season["PRCP"].sum() / 10.0, 1)


def compute_vintage_risk_score(
    winkler_gdd: float, mean_gdd: float,
    heat_events: int, mean_heat_events: float,
    last_spring_frost: str, mean_spring_frost_doy: float,
    frost_free_days: int,
) -> int:
    """Compute Vintage Quality Risk Score (0-100). 100 = ideal."""
    score = 100

    # GDD deviation
    if mean_gdd > 0:
        pct_diff = (winkler_gdd - mean_gdd) / mean_gdd * 100
        if pct_diff > 15:
            score -= 10
        elif pct_diff < -15:
            score -= 8

    # Excess heat events: -5 each above historical average
    if mean_heat_events > 0:
        excess = max(0, heat_events - mean_heat_events)
        score -= int(excess) * 5

    # Late spring frost penalty
    if last_spring_frost and mean_spring_frost_doy:
        frost_doy = pd.Timestamp(last_spring_frost).dayofyear
        if frost_doy > mean_spring_frost_doy + 15:
            score -= 10

    return max(0, min(100, score))


def generate_demo_data():
    """Generate realistic synthetic data for Napa Valley and Willamette Valley, 5 years."""
    np.random.seed(42)
    demo_regions = ["Napa Valley", "Willamette Valley"]
    years = range(2018, 2023)

    # Realistic GDD baselines (Napa ~3200-3600, Willamette ~2100-2500)
    baselines = {
        "Napa Valley": {"gdd_mean": 3400, "gdd_std": 200, "heat_mean": 12, "frost_spring_doy": 65, "precip_mean": 80},
        "Willamette Valley": {"gdd_mean": 2300, "gdd_std": 180, "heat_mean": 3, "frost_spring_doy": 95, "precip_mean": 200},
    }

    all_rows = []
    timeseries_data = {}

    for region_name in demo_regions:
        b = baselines[region_name]
        region_results = []
        timeseries_data[region_name] = {}

        for year in years:
            gdd = max(1500, b["gdd_mean"] + np.random.normal(0, b["gdd_std"]))
            heat_events = max(0, int(b["heat_mean"] + np.random.normal(0, 3)))
            spring_frost_doy = max(32, int(b["frost_spring_doy"] + np.random.normal(0, 10)))
            fall_frost_doy = min(365, max(280, int(310 + np.random.normal(0, 12))))
            precip = max(10, b["precip_mean"] + np.random.normal(0, 30))
            frost_free = fall_frost_doy - spring_frost_doy

            spring_date = (pd.Timestamp(year, 1, 1) + pd.Timedelta(days=spring_frost_doy - 1)).strftime("%Y-%m-%d")
            fall_date = (pd.Timestamp(year, 1, 1) + pd.Timedelta(days=fall_frost_doy - 1)).strftime("%Y-%m-%d")

            region_results.append({"winkler_gdd": round(gdd, 1), "year": year})

            mean_gdd = b["gdd_mean"]
            gdd_vs_mean = round((gdd - mean_gdd) / mean_gdd * 100, 1)

            risk = compute_vintage_risk_score(
                gdd, mean_gdd, heat_events, b["heat_mean"],
                spring_date, b["frost_spring_doy"], frost_free,
            )

            all_rows.append({
                "region": region_name,
                "year": year,
                "winkler_gdd": round(gdd, 1),
                "winkler_region": classify_winkler(gdd),
                "last_spring_frost": spring_date,
                "first_fall_frost": fall_date,
                "frost_free_days": frost_free,
                "heat_events_count": heat_events,
                "season_precip_mm": round(precip, 1),
                "vintage_risk_score": risk,
                "gdd_vs_mean_pct": gdd_vs_mean,
                "data_source": "synthetic_demo",
            })

            # Generate daily GDD timeseries for this region-year
            season_dates = pd.date_range(f"{year}-04-01", f"{year}-10-31", freq="D")
            n_days = len(season_dates)
            daily_gdd_values = np.maximum(0, np.random.normal(gdd / n_days, 3, n_days))
            # Scale so cumulative matches target
            daily_gdd_values = daily_gdd_values / daily_gdd_values.sum() * gdd
            cumulative = np.cumsum(daily_gdd_values)

            ts_df = pd.DataFrame({
                "cumulative_gdd": cumulative,
                "daily_gdd": daily_gdd_values,
            }, index=season_dates)
            ts_df.index.name = "date"
            timeseries_data[region_name][year] = ts_df

    return all_rows, timeseries_data


def run_full_pipeline():
    """Run the full pipeline with real NOAA data."""
    from .stations import get_station_mapping
    from .fetch import fetch_station_year

    import os
    token = os.environ.get("NOAA_TOKEN", "")
    if not token:
        print("ERROR: NOAA_TOKEN not set. Use --demo mode or set token in .env")
        sys.exit(1)

    station_mapping = get_station_mapping()
    years = range(2000, 2024)

    all_rows = []
    timeseries_data = {}

    for region in REGIONS:
        stations = station_mapping.get(region.name, region.fallback_stations)
        if not stations:
            continue

        primary_station = stations[0]
        region_gdd_results = []
        region_frost_results = []
        timeseries_data[region.name] = {}

        for year in years:
            records = fetch_station_year(primary_station, year, token)
            daily_df = parse_noaa_records(records)

            if daily_df.empty:
                continue

            winkler = compute_winkler_index(daily_df, year)
            frost = detect_frost_dates(daily_df, year)
            heat = compute_heat_events(daily_df, year)
            precip = compute_season_precip(daily_df, year)

            region_gdd_results.append(winkler)
            region_frost_results.append(frost)
            timeseries_data[region.name][year] = winkler["daily_gdd"]

        mean_gdd = compute_historical_mean(region_gdd_results)
        frost_avgs = compute_historical_frost_averages(region_frost_results)
        mean_heat = np.mean([compute_heat_events(
            parse_noaa_records(fetch_station_year(stations[0], y, token)), y
        ) for y in range(2000, 2023) if y in [r["year"] for r in region_gdd_results]]) if region_gdd_results else 0

        for winkler, frost in zip(region_gdd_results, region_frost_results):
            gdd_vs_mean = round((winkler["winkler_gdd"] - mean_gdd) / mean_gdd * 100, 1) if mean_gdd else 0

            risk = compute_vintage_risk_score(
                winkler["winkler_gdd"], mean_gdd,
                0, mean_heat,
                frost["last_spring_frost"],
                frost_avgs.get("avg_last_spring_frost_doy", 80),
                frost["frost_free_days"] or 0,
            )

            all_rows.append({
                "region": region.name,
                "year": winkler["year"],
                "winkler_gdd": winkler["winkler_gdd"],
                "winkler_region": winkler["winkler_region"],
                "last_spring_frost": frost["last_spring_frost"],
                "first_fall_frost": frost["first_fall_frost"],
                "frost_free_days": frost["frost_free_days"],
                "heat_events_count": 0,
                "season_precip_mm": 0,
                "vintage_risk_score": risk,
                "gdd_vs_mean_pct": gdd_vs_mean,
                "data_source": "noaa_ghcnd",
            })

    return all_rows, timeseries_data


def main():
    parser = argparse.ArgumentParser(description="NOAA Wine Climate Pipeline — compute viticulture metrics")
    parser.add_argument("--demo", action="store_true", help="Use synthetic demo data (no NOAA token needed)")
    args = parser.parse_args()

    if args.demo:
        print("Running in DEMO mode with synthetic data for Napa Valley and Willamette Valley...")
        all_rows, timeseries_data = generate_demo_data()
    else:
        print("Running full pipeline with NOAA data...")
        all_rows, timeseries_data = run_full_pipeline()

    if not all_rows:
        print("No data produced. Exiting.")
        sys.exit(1)

    latest_year = max(r["year"] for r in all_rows)
    print(f"Writing output files for {len(all_rows)} region-year records...")

    write_by_region_year(all_rows)
    write_winkler_heatmap(all_rows)
    write_gdd_timeseries(timeseries_data)
    write_vintage_signals(all_rows, latest_year)
    write_summary_json(all_rows, latest_year)

    print(f"Done. Output written to data/processed/")
    print(f"  - by_region_year.csv ({len(all_rows)} rows)")
    print(f"  - winkler_heatmap.csv")
    print(f"  - gdd_timeseries.csv")
    print(f"  - vintage_signals.csv")
    print(f"  - summary.json")


if __name__ == "__main__":
    main()
