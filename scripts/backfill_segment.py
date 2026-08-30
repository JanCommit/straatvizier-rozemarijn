"""Backfill één vast Telraam-segment naar Supabase.

Gericht hulpscript dat momenteel Rozemarijnstraat (segment 155073) gebruikt. Pas
vaste segment- en periodeconstanten alleen bewust aan wanneer dit script opnieuw nodig is."""

import os
import time
from datetime import datetime, timezone

import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

TELRAAM_API_KEY = os.getenv("TELRAAM_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not TELRAAM_API_KEY:
    raise RuntimeError("TELRAAM_API_KEY ontbreekt in .env")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL ontbreekt in .env")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY ontbreekt in .env")


TELRAAM_API_URL = "https://telraam-api.net/v1/reports/traffic"

TELRAAM_SEGMENT_ID = 155073
STREET_NAME = "Rozemarijnstraat"

START_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


def get_database_segment_id() -> int:
    """Zoek onze interne Supabase-ID voor het Telraam-segment."""

    response = (
        supabase
        .table("segments")
        .select("id")
        .eq("telraam_segment_id", TELRAAM_SEGMENT_ID)
        .single()
        .execute()
    )

    return response.data["id"]


def fetch_telraam_period(
    start: datetime,
    end: datetime,
) -> list[dict]:
    """Haal één periode uurdata op bij Telraam."""

    payload = {
        "id": str(TELRAAM_SEGMENT_ID),
        "time_start": start.strftime("%Y-%m-%d %H:%M:%SZ"),
        "time_end": end.strftime("%Y-%m-%d %H:%M:%SZ"),
        "level": "segments",
        "format": "per-hour",
    }

    headers = {
        "X-Api-Key": TELRAAM_API_KEY,
        "Content-Type": "application/json",
    }

    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                TELRAAM_API_URL,
                headers=headers,
                json=payload,
                timeout=90,
            )

            response.raise_for_status()

            return response.json().get("report", [])

        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
        ) as exc:

            status_code = (
                exc.response.status_code
                if isinstance(exc, requests.HTTPError)
                and exc.response is not None
                else None
            )

            retryable = (
                status_code in {429, 500, 502, 503, 504}
                or status_code is None
            )

            if not retryable or attempt == max_attempts:
                raise

            wait_seconds = attempt * 5

            print(
                f"\n    Tijdelijke Telraam-fout: {exc}"
            )
            print(
                f"    Nieuwe poging over {wait_seconds} seconden "
                f"({attempt}/{max_attempts})..."
            )

            time.sleep(wait_seconds)

    return []


def transform_record(
    record: dict,
    database_segment_id: int,
) -> dict:
    """Vertaal één Telraam-record naar ons databaseschema."""

    return {
        "segment_id": database_segment_id,
        "measured_at": record["date"],

        "uptime": record.get("uptime"),

        "heavy": record.get("heavy"),
        "car": record.get("car"),
        "bike": record.get("bike"),
        "pedestrian": record.get("pedestrian"),
        "night": record.get("night"),

        "heavy_left": record.get("heavy_lft"),
        "heavy_right": record.get("heavy_rgt"),

        "car_left": record.get("car_lft"),
        "car_right": record.get("car_rgt"),

        "bike_left": record.get("bike_lft"),
        "bike_right": record.get("bike_rgt"),

        "pedestrian_left": record.get("pedestrian_lft"),
        "pedestrian_right": record.get("pedestrian_rgt"),

        "night_left": record.get("night_lft"),
        "night_right": record.get("night_rgt"),

        "direction": record.get("direction"),
        "timezone": record.get("timezone"),
    }


def save_records(records: list[dict]) -> None:
    """UPSERT records in kleinere batches naar Supabase."""

    if not records:
        return

    batch_size = 500

    for start_index in range(0, len(records), batch_size):
        batch = records[
            start_index:start_index + batch_size
        ]

        (
            supabase
            .table("measurements")
            .upsert(
                batch,
                on_conflict="segment_id,measured_at",
            )
            .execute()
        )


def main():
    print("=" * 70)
    print("STRAATVIZIER HISTORISCHE BACKFILL")
    print("=" * 70)
    print(f"Straat:          {STREET_NAME}")
    print(f"Telraam segment: {TELRAAM_SEGMENT_ID}")
    print(f"Vanaf:           {START_DATE:%Y-%m-%d}")
    print(f"Tot:             {END_DATE:%Y-%m-%d}")
    print()

    database_segment_id = get_database_segment_id()

    print(
        f"Supabase segment-ID gevonden: "
        f"{database_segment_id}"
    )
    print()

    current = START_DATE
    total_downloaded = 0
    total_saved = 0
    failed_periods = []

    while current < END_DATE:

        period_end = min(
            current + relativedelta(months=1),
            END_DATE,
        )

        print(
            f"{current:%Y-%m-%d} → "
            f"{period_end:%Y-%m-%d}",
            end=" ... ",
            flush=True,
        )

        try:
            raw_records = fetch_telraam_period(
                current,
                period_end,
            )

            transformed = [
                transform_record(
                    record,
                    database_segment_id,
                )
                for record in raw_records
            ]

            save_records(transformed)

            total_downloaded += len(raw_records)
            total_saved += len(transformed)

            print(
                f"{len(raw_records):5d} records opgeslagen ✓"
            )

        except Exception as exc:
            print(f"FOUT ✗")
            print(f"    {exc}")

            failed_periods.append(
                (
                    current.strftime("%Y-%m-%d"),
                    period_end.strftime("%Y-%m-%d"),
                )
            )

        # Respecteer Telraam rate limiting.
        time.sleep(1.1)

        current = period_end

    print()
    print("=" * 70)
    print("BACKFILL KLAAR")
    print("=" * 70)
    print(f"Records opgehaald:   {total_downloaded}")
    print(f"Records verwerkt:    {total_saved}")

    if failed_periods:
        print()
        print("MISLUKTE PERIODES:")

        for start, end in failed_periods:
            print(f"  {start} → {end}")

    else:
        print("Mislukte periodes:   geen ✓")


if __name__ == "__main__":
    main()