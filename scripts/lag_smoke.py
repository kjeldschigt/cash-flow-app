"""
Lag analytics smoke test.

Runs lead_to_booking_lag over a broad date range and prints the summary
and the first 5 rows of the lag table for quick verification.

Usage:
  python scripts/lag_smoke.py
"""
from __future__ import annotations

import os
import sys
from pprint import pprint

# Allow running this script directly without setting PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.repositories.base import DatabaseConnection  # noqa: E402
from src.services.analytics_service import AnalyticsService  # noqa: E402


def main() -> None:
    # Resolve DB path without importing Settings (to avoid pydantic).
    db_path = os.environ.get("CASHFLOW_DB_PATH", "cashflow.db")
    print(f"Using DB: {db_path}")

    db = DatabaseConnection(db_path)
    analytics_service = AnalyticsService(db)

    start = "2024-01-01"
    end = "2025-12-31"
    print(f"\nComputing Lead → Booking Lag for range [{start} .. {end}]...")
    result = analytics_service.lead_to_booking_lag(start, end)

    summary = result.get("summary", {})
    print("\nSummary:")
    pprint(summary)

    lag_table = result.get("lag_table", [])
    print(f"\nLag Table — showing first {min(5, len(lag_table))} rows (of {len(lag_table)} total returned):")
    for i, row in enumerate(lag_table[:5], start=1):
        print(f"Row {i}:")
        pprint(row)


if __name__ == "__main__":
    main()
