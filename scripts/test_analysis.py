"""Handmatig diagnostisch script voor analysefuncties op databasegegevens.

Dit is geen geautomatiseerde pytest-test. Het voert rechtstreeks voorbeeldcode uit
en kan daardoor verouderen wanneer de analyse- of database-API verandert."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(PROJECT_ROOT / "src"),
)

from straatvizier.analysis import (
    prepare_measurements,
    filter_measurements,
    daily_totals,
    monthly_average_daily_traffic,
)
from straatvizier.database import get_measurements


SEGMENT_ID = 1


df = get_measurements(
    segment_id=SEGMENT_ID,
    start_date="2024-01-01",
    end_date="2025-01-01",
)

print("Ruwe records:", len(df))

df = prepare_measurements(df)

df = filter_measurements(
    df,
    start_hour=8,
    end_hour=18,
    min_uptime=0.5,
)

print("Records na filtering:", len(df))

daily = daily_totals(
    df,
    mode="car",
)

print("Dagen:", len(daily))

monthly = monthly_average_daily_traffic(
    daily,
    min_hours_per_day=8,
)

print()
print(monthly)