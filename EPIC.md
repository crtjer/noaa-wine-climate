# NOAA Wine Climate Pipeline — EPIC

## What This Is

A pipeline that pulls daily weather data from NOAA's Climate Data Online (CDO) API for
every major US wine AVA (American Viticultural Area), then computes the viticulture-specific
metrics that growers, vineyard managers, distributors, and crop insurers actually use.

The core output: **Growing Degree Day (GDD) accumulation by region and year** — the single
most important signal for predicting harvest timing, ripeness potential, and vintage quality.

## Source

NOAA National Centers for Environmental Information (NCEI)
- API: `https://www.ncei.noaa.gov/cdo-web/api/v2/`
- Dataset: GHCND (Global Historical Climatology Network Daily) — daily TMAX, TMIN, PRCP
- Token: free, register at `https://www.ncdc.noaa.gov/cdo-web/token`
- Rate limit: 5 req/sec, 10,000 req/day

## Key Viticulture Metrics

### 1. Growing Degree Days (GDD) — Winkler Scale
**Formula:** GDD_day = max(0, (TMAX_F + TMIN_F) / 2 - 50)
**Season:** April 1 – October 31 (standard US viticulture window)
**Cumulative GDD = Winkler Index** for the season

| Winkler Region | GDD Range | Climate | Best Varieties |
|---|---|---|---|
| I | < 2,500 | Very cool | Pinot Noir, Chardonnay, Riesling |
| II | 2,500–3,000 | Cool-moderate | Cabernet, Merlot, Sauvignon Blanc |
| III | 3,000–3,500 | Moderate-warm | Zinfandel, Syrah, Grenache |
| IV | 3,500–4,000 | Warm | Most varieties ripen fully |
| V | > 4,000 | Very hot | Table grapes, raisins |

### 2. Last Spring Frost Date
Date of last temperature ≤ 32°F in spring. Critical for bud break risk.
Expressed as: day-of-year, calendar date, and days since Jan 1.

### 3. First Fall Frost Date
Date of first temperature ≤ 32°F in fall. Determines harvest window closure.

### 4. Frost-Free Growing Season Length
Days between last spring frost and first fall frost.

### 5. Heat Events (>95°F / >35°C days)
Count of days exceeding heat threshold during growing season.
Heat spikes during veraison and ripening reduce quality.

### 6. Season Precipitation (Apr–Oct)
Total precipitation during growing season. Low = quality; High = disease pressure.

### 7. Vintage Quality Risk Score (derived)
Composite signal: 
- GDD vs historical average (±10% = normal, >10% = hot vintage, <10% = cool)
- Heat event count vs historical average
- Late frost risk (last frost date vs historical)
- GDD rate in Aug–Sep (critical ripening window)

## Target Wine Regions (AVAs)

| Region | State | Representative Zip | Key Varieties |
|---|---|---|---|
| Napa Valley | CA | 94558 | Cabernet Sauvignon, Chardonnay |
| Sonoma County | CA | 95476 | Pinot Noir, Zinfandel, Chardonnay |
| Russian River Valley | CA | 95403 | Pinot Noir, Chardonnay |
| Paso Robles | CA | 93446 | Cabernet, Zinfandel, Rhône varieties |
| Central Coast | CA | 93401 | Chardonnay, Pinot Noir |
| Mendocino | CA | 95460 | Zinfandel, Pinot Noir |
| Willamette Valley | OR | 97128 | Pinot Noir, Pinot Gris |
| Columbia Valley | WA | 99301 | Cabernet, Riesling, Chardonnay |
| Walla Walla | WA | 99362 | Cabernet, Syrah, Merlot |
| Finger Lakes | NY | 14456 | Riesling, Gewürztraminer |
| Lodi | CA | 95240 | Zinfandel, Cabernet |
| Alexander Valley | CA | 95448 | Cabernet Sauvignon |

## Pipeline Architecture

```
pipeline/
  regions.py       — AVA region definitions (name, zip, lat/lon, station IDs)
  fetch.py         — NOAA CDO API client with rate limiting + caching
  stations.py      — find best weather stations for each region
  gdd.py           — GDD calculation (Winkler method)
  frost.py         — last/first frost date detection
  metrics.py       — all derived metrics per region per year
  export.py        — write final outputs

data/
  raw/             — cached API responses (gitignored)
  processed/
    by_region_year.csv      — one row per region × year (all metrics)
    gdd_timeseries.csv      — daily GDD accumulation per region (wide format, years as cols)
    frost_dates.csv         — spring/fall frost dates by region × year
    vintage_signals.csv     — risk scores and quality signals
    summary.json            — latest season snapshot + regional comparison
    winkler_heatmap.csv     — Winkler index by region × year (great for viz)

scripts/
  run_pipeline.sh  — full pipeline
  update_season.sh — update current season only

.env.example
requirements.txt
README.md
EPIC.md
```

## Stories

### NOAA-001 — Region definitions and station discovery
**Files:** `pipeline/regions.py`, `pipeline/stations.py`

Define all 12 AVA regions with zip codes. Query NOAA station search API to find the
best reporting station(s) for each region (closest, most complete GHCND record).
Cache station IDs to avoid repeated lookups.

**ACs:**
- All 12 regions defined with name, state, zip, lat/lon
- Each region mapped to 1–3 best GHCND station IDs
- Station selection: prefer stations with >90% data completeness back to 2000
- Station mapping saved to `data/processed/stations.json`

### NOAA-002 — NOAA API client with caching and rate limiting
**Files:** `pipeline/fetch.py`

Wrap NOAA CDO API v2. Handle:
- Token from env var `NOAA_TOKEN`
- Rate limit: max 5 req/sec (use time.sleep between calls)
- Pagination (API returns max 1,000 records per request)
- Cache raw responses to `data/raw/` as JSON files keyed by (dataset, station, year)
- Skip cached files on re-run — only fetch what's missing
- Retry on 429/503 with exponential backoff

**ACs:**
- Can fetch GHCND daily data (TMAX, TMIN, PRCP) for any station + year range
- Cached correctly — re-running doesn't hit API for existing data
- Rate limiting verified — no 429 errors on full run

### NOAA-003 — GDD calculation (Winkler method)
**Files:** `pipeline/gdd.py`

Calculate daily and cumulative GDD for each station × year.

**Formula:**
```python
# Convert NOAA tenths-of-degrees-C to Fahrenheit
tmax_f = (tmax_raw / 10 * 9/5) + 32
tmin_f = (tmin_raw / 10 * 9/5) + 32
daily_gdd = max(0, (tmax_f + tmin_f) / 2 - 50)
```

**Season window:** April 1 (day 91) – October 31 (day 304)
**Handle missing days:** interpolate from adjacent days if gap ≤ 3 days; flag if larger gap

**ACs:**
- GDD calculated correctly for all region × year combinations
- Cumulative GDD from Apr 1 is the Winkler Index for the season
- Missing data handled and flagged
- Historical mean GDD (2000–2020) computed per region as baseline

### NOAA-004 — Frost date detection
**Files:** `pipeline/frost.py`

Find last spring frost (≤32°F) and first fall frost (≤32°F) per region × year.

**ACs:**
- Last spring frost: latest date in Jan–Jun where TMIN ≤ 32°F
- First fall frost: earliest date in Aug–Dec where TMIN ≤ 32°F
- Frost-free season = days between those two dates
- Handle years with no frost (return null with flag)
- Historical average frost dates computed per region (2000–2020 baseline)

### NOAA-005 — Full metrics computation and export
**Files:** `pipeline/metrics.py`, `pipeline/export.py`

Compute all 7 metrics for every region × year. Write all output files.

**Derived: Vintage Quality Risk Score (0–100)**
- 100 = ideal conditions (GDD ≈ regional mean, low heat events, good frost timing)
- Deductions: excess heat events (-5 each), very late spring frost (-10), GDD >15% above mean (-10), GDD >15% below mean (-8), excess precipitation (-5)

**ACs:**
- `by_region_year.csv`: region, year, winkler_gdd, winkler_region (I-V), last_frost_date, first_frost_date, frost_free_days, heat_events_count, season_precip_mm, vintage_risk_score, gdd_vs_mean_pct
- `winkler_heatmap.csv`: regions as rows, years as columns, GDD values
- `gdd_timeseries.csv`: daily cumulative GDD for each region (current year vs prior 5 years)
- `vintage_signals.csv`: current year only — all signals + risk flags
- `summary.json`: latest season snapshot, hottest/coolest regions, highest/lowest risk

### NOAA-006 — Wire up CLI and README
**Files:** `scripts/run_pipeline.sh`, `scripts/update_season.sh`, `README.md`, `.env.example`

README must explain:
1. What GDD is and why it matters for wine
2. The Winkler scale (table)
3. How to get a NOAA token (link + 30-second instructions)
4. How to run the full pipeline
5. How to run just the current season update
6. Description of every output file and what it tells you
7. Example use cases for each stakeholder type (grower, distributor, insurer)

.env.example:
```
NOAA_TOKEN=your_token_here   # Get free at: https://www.ncdc.noaa.gov/cdo-web/token
```

## Notes on Data Quality

- GHCND stations: some have gaps. If primary station missing >30 days in a season,
  fall back to secondary station for that region.
- NOAA stores TMAX/TMIN in tenths of degrees Celsius. Always divide by 10 before converting.
- Some early years (pre-2000) have sparser coverage in smaller AVAs.
- The pipeline covers 2000–present by default. Current-season data available ~24hr lag.
