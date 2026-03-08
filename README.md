# NOAA Wine Climate Pipeline

A data pipeline that pulls daily weather data from NOAA's Climate Data Online (CDO) API for 12 major US wine AVAs (American Viticultural Areas) and computes viticulture-specific metrics used by growers, distributors, and crop insurers.

## What is GDD and Why It Matters

**Growing Degree Days (GDD)** measure accumulated heat during the growing season (April 1 – October 31). It's the single most important climate metric for viticulture — it predicts harvest timing, grape ripeness, and vintage quality.

**Formula:** `GDD = max(0, (TMAX°F + TMIN°F) / 2 - 50)`

The cumulative GDD for a season is the **Winkler Index**, which classifies wine regions into climate zones:

| Winkler Region | GDD Range | Climate | Best Varieties |
|---|---|---|---|
| I | < 2,500 | Very cool | Pinot Noir, Chardonnay, Riesling |
| II | 2,500–3,000 | Cool-moderate | Cabernet, Merlot, Sauvignon Blanc |
| III | 3,000–3,500 | Moderate-warm | Zinfandel, Syrah, Grenache |
| IV | 3,500–4,000 | Warm | Most varieties ripen fully |
| V | > 4,000 | Very hot | Table grapes, raisins |

## Getting a NOAA Token

1. Visit https://www.ncdc.noaa.gov/cdo-web/token
2. Enter your email address
3. You'll receive a token via email within minutes
4. Add it to your `.env` file:
   ```
   NOAA_TOKEN=your_token_here
   ```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your NOAA_TOKEN
```

## Running the Pipeline

### Full pipeline (requires NOAA token)
```bash
bash scripts/run_pipeline.sh
```

### Demo mode (no token needed — uses synthetic data)
```bash
bash scripts/run_pipeline.sh --demo
# or
python -m pipeline.metrics --demo
```

## Output Files

All outputs are written to `data/processed/`:

| File | Description |
|---|---|
| `by_region_year.csv` | One row per region × year with all metrics: GDD, Winkler region, frost dates, heat events, precipitation, vintage risk score |
| `winkler_heatmap.csv` | Pivot table — regions as rows, years as columns, GDD values. Ready for heatmap visualization |
| `gdd_timeseries.csv` | Daily cumulative GDD for each region and year. Shows heat accumulation curves |
| `vintage_signals.csv` | Current/latest year only — all metrics plus hot/cool vintage flags |
| `summary.json` | Latest season snapshot: hottest/coolest regions, highest/lowest risk scores |

## Covered Wine Regions

| Region | State | Key Varieties |
|---|---|---|
| Napa Valley | CA | Cabernet Sauvignon, Chardonnay |
| Sonoma County | CA | Pinot Noir, Zinfandel, Chardonnay |
| Russian River Valley | CA | Pinot Noir, Chardonnay |
| Paso Robles | CA | Cabernet, Zinfandel, Rhône varieties |
| Central Coast | CA | Chardonnay, Pinot Noir |
| Mendocino | CA | Zinfandel, Pinot Noir |
| Willamette Valley | OR | Pinot Noir, Pinot Gris |
| Columbia Valley | WA | Cabernet, Riesling, Chardonnay |
| Walla Walla | WA | Cabernet, Syrah, Merlot |
| Finger Lakes | NY | Riesling, Gewürztraminer |
| Lodi | CA | Zinfandel, Cabernet |
| Alexander Valley | CA | Cabernet Sauvignon |

## Use Cases

- **Growers/Vineyard Managers:** Track GDD accumulation to predict harvest dates, compare current season to historical norms, identify frost risk windows
- **Wine Distributors:** Assess vintage quality signals across regions to inform purchasing and pricing decisions
- **Crop Insurers:** Quantify climate risk per region using frost dates, heat events, and GDD deviation from historical baselines

## Data Source

NOAA National Centers for Environmental Information (NCEI), GHCND dataset.
- API: `https://www.ncei.noaa.gov/cdo-web/api/v2/`
- Rate limit: 5 requests/second, 10,000 requests/day
- Data coverage: 2000–present (daily TMAX, TMIN, PRCP)
