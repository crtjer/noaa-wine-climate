"""NOAA-005 (part 2): Export pipeline results to CSV and JSON output files."""

import json
from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path("data/processed")


def write_by_region_year(rows: list):
    """Write by_region_year.csv — one row per region x year with all metrics."""
    df = pd.DataFrame(rows)
    cols = [
        "region", "year", "winkler_gdd", "winkler_region",
        "last_spring_frost", "first_fall_frost", "frost_free_days",
        "heat_events_count", "season_precip_mm",
        "vintage_risk_score", "gdd_vs_mean_pct", "data_source",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    df = df[cols].sort_values(["region", "year"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "by_region_year.csv", index=False)
    return df


def write_winkler_heatmap(rows: list):
    """Write winkler_heatmap.csv — regions as rows, years as columns, GDD values."""
    df = pd.DataFrame(rows)
    if df.empty:
        return
    pivot = df.pivot_table(index="region", columns="year", values="winkler_gdd", aggfunc="first")
    pivot.columns = [str(int(c)) for c in pivot.columns]
    pivot = pivot.sort_index()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pivot.to_csv(OUTPUT_DIR / "winkler_heatmap.csv")
    return pivot


def write_gdd_timeseries(timeseries_data: dict):
    """Write gdd_timeseries.csv — daily cumulative GDD per region.

    timeseries_data: {region_name: {year: DataFrame with cumulative_gdd column}}
    """
    all_frames = []
    for region, year_data in timeseries_data.items():
        for year, gdd_df in year_data.items():
            series = gdd_df[["cumulative_gdd"]].copy()
            series = series.rename(columns={"cumulative_gdd": "gdd"})
            series["region"] = region
            series["year"] = year
            series["day_of_year"] = series.index.dayofyear
            all_frames.append(series.reset_index())
    if not all_frames:
        return
    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.rename(columns={"index": "date"})
    combined = combined[["region", "year", "date", "day_of_year", "gdd"]]
    combined = combined.sort_values(["region", "year", "date"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_DIR / "gdd_timeseries.csv", index=False)


def write_vintage_signals(rows: list, latest_year: int):
    """Write vintage_signals.csv — current/latest year only with risk flags."""
    df = pd.DataFrame(rows)
    current = df[df["year"] == latest_year].copy()
    if current.empty:
        return
    current["hot_vintage_flag"] = current["gdd_vs_mean_pct"] > 10
    current["cool_vintage_flag"] = current["gdd_vs_mean_pct"] < -10
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    current.to_csv(OUTPUT_DIR / "vintage_signals.csv", index=False)


def write_summary_json(rows: list, latest_year: int):
    """Write summary.json — latest season snapshot + regional comparison."""
    df = pd.DataFrame(rows)
    current = df[df["year"] == latest_year]
    if current.empty:
        return

    summary = {
        "latest_year": latest_year,
        "regions_count": len(current),
        "hottest_region": None,
        "coolest_region": None,
        "highest_risk": None,
        "lowest_risk": None,
        "regions": [],
    }

    if not current.empty:
        hottest_idx = current["winkler_gdd"].idxmax()
        coolest_idx = current["winkler_gdd"].idxmin()
        summary["hottest_region"] = current.loc[hottest_idx, "region"]
        summary["coolest_region"] = current.loc[coolest_idx, "region"]

        if "vintage_risk_score" in current.columns:
            highest_idx = current["vintage_risk_score"].idxmin()
            lowest_idx = current["vintage_risk_score"].idxmax()
            summary["highest_risk"] = current.loc[highest_idx, "region"]
            summary["lowest_risk"] = current.loc[lowest_idx, "region"]

        for _, row in current.iterrows():
            summary["regions"].append({
                "region": row["region"],
                "winkler_gdd": row.get("winkler_gdd"),
                "winkler_region": row.get("winkler_region"),
                "vintage_risk_score": row.get("vintage_risk_score"),
                "frost_free_days": row.get("frost_free_days"),
            })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
