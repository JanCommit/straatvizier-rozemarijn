import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL ontbreekt")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY ontbreekt")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


def get_streets() -> pd.DataFrame:
    """Geef alle gekende straten en segmenten terug."""

    response = (
        supabase
        .table("segments")
        .select(
            "id, telraam_segment_id, name, "
            "streets(id, name)"
        )
        .execute()
    )

    rows = []

    for segment in response.data:
        rows.append({
            "segment_id": segment["id"],
            "telraam_segment_id":
                segment["telraam_segment_id"],
            "segment_name": segment["name"],
            "street_id": segment["streets"]["id"],
            "street": segment["streets"]["name"],
        })

    return pd.DataFrame(rows)


def get_measurements(
    segment_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    """
    Lees alle uurmetingen voor één segment.

    Supabase/PostgREST geeft resultaten in beperkte batches terug,
    daarom halen we de data gepagineerd op.
    """

    page_size = 1000
    offset = 0
    all_rows = []

    while True:
        query = (
            supabase
            .table("measurements")
            .select(
                "measured_at,"
                "uptime,"
                "car,"
                "bike,"
                "heavy,"
                "pedestrian,"
                "night,"
                "car_left,"
                "car_right,"
                "bike_left,"
                "bike_right,"
                "heavy_left,"
                "heavy_right"
            )
            .eq("segment_id", segment_id)
            .order("measured_at")
            .range(offset, offset + page_size - 1)
        )

        if start_date:
            query = query.gte(
                "measured_at",
                start_date,
            )

        if end_date:
            query = query.lt(
                "measured_at",
                end_date,
            )

        response = query.execute()

        rows = response.data

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(all_rows)

    if not df.empty:
        df["measured_at"] = pd.to_datetime(
            df["measured_at"],
            utc=True,
        )

    return df