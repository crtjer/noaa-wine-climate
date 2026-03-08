#!/usr/bin/env bash
# Run the full NOAA wine climate pipeline.
# Requires NOAA_TOKEN in .env or environment.
# Use --demo flag to run with synthetic data (no token needed).

set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== NOAA Wine Climate Pipeline ==="

if [ "${1:-}" = "--demo" ]; then
    echo "Running in demo mode..."
    python3 -m pipeline.metrics --demo
else
    if [ -f .env ]; then
        export $(grep -v '^#' .env | xargs)
    fi
    if [ -z "${NOAA_TOKEN:-}" ]; then
        echo "ERROR: NOAA_TOKEN not set. Either:"
        echo "  1. Create .env with NOAA_TOKEN=your_token"
        echo "  2. Run with --demo flag: $0 --demo"
        exit 1
    fi
    python3 -m pipeline.metrics
fi

echo ""
echo "=== Output Files ==="
ls -la data/processed/
