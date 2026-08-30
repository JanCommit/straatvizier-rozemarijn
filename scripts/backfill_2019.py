"""Vul de expliciet gedefinieerde StraatVizier-segmenten uit 2019 historisch aan.

Gericht migratie/backfillscript voor de periode vóór de algemene backfill vanaf
2020. De doelstraten en hun exacte historische intervallen staan bewust in dit bestand."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TELRAAM_API_KEY = os.getenv("TELRAAM_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not TELRAAM_API_KEY:
    raise RuntimeError("TELRAAM_API_KEY ontbreekt in .env")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL ontbreekt in .env")
if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY ontbreekt in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

TELRAAM_API_URL = "https://telraam-api.net/v1/reports/traffic"

TARGETS = [
    ("Rozemarijnstraat", 155073,
     datetime(2019, 4, 9, tzinfo=timezone.utc),
     datetime(2020, 1, 1, tzinfo=timezone.utc)),
    ("Annonciadenstraat", 154163,
     datetime(2019, 9, 11, tzinfo=timezone.utc),
     datetime(2020, 1, 1, tzinfo=timezone.utc)),
]


def get_db_segment_id(telraam_segment_id):
    response = (
        supabase.table("segments")
        .select("id")
        .eq("telraam_segment_id", telraam_segment_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        raise RuntimeError(
            f"Geen Supabase-segment gevonden voor {telraam_segment_id}"
        )
    return int(response.data[0]["id"])


def fetch_period(telraam_segment_id, start, end):
    payload = {
        "id": str(telraam_segment_id),
        "time_start": start.strftime("%Y-%m-%d %H:%M:%SZ"),
        "time_end": end.strftime("%Y-%m-%d %H:%M:%SZ"),
        "level": "segments",
        "format": "per-hour",
    }
    headers = {
        "X-Api-Key": TELRAAM_API_KEY,
        "Content-Type": "application/json",
    }

    for attempt in range(1, 6):
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
            status = (
                exc.response.status_code
                if isinstance(exc, requests.HTTPError)
                and exc.response is not None
                else None
            )
            if status not in {None, 429, 500, 502, 503, 504} or attempt == 5:
                raise
            wait = attempt * 5
            print(f"      Tijdelijke API-fout: {exc}")
            print(f"      Nieuwe poging over {wait}s ({attempt}/5)")
            time.sleep(wait)

    return []


def transform_record(record, database_segment_id):
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
        "v85": record.get("v85"),
        "car_speed_hist_0to120plus": record.get("car_speed_hist_0to120plus"),
        "direction": record.get("direction"),
        "timezone": record.get("timezone"),
    }


def save_records(records):
    for i in range(0, len(records), 500):
        (
            supabase.table("measurements")
            .upsert(
                records[i:i + 500],
                on_conflict="segment_id,measured_at",
            )
            .execute()
        )


def backfill(street, telraam_segment_id, start, end):
    db_segment_id = get_db_segment_id(telraam_segment_id)

    print()
    print("=" * 72)
    print(f"{street} ({telraam_segment_id})")
    print("=" * 72)

    current = start
    downloaded = 0
    empty = 0
    failed = []

    while current < end:
        period_end = min(current + relativedelta(months=1), end)
        label = f"{current:%Y-%m-%d} → {period_end:%Y-%m-%d}"
        print(f"{label} ... ", end="", flush=True)

        try:
            raw = fetch_period(telraam_segment_id, current, period_end)
            if not raw:
                print("geen data")
                empty += 1
            else:
                records = [
                    transform_record(r, db_segment_id)
                    for r in raw
                ]
                save_records(records)
                downloaded += len(records)
                print(f"{len(records):5d} records opgeslagen ✓")
        except Exception as exc:
            print("FOUT ✗")
            print(f"      {exc}")
            failed.append(label)

        time.sleep(1.1)
        current = period_end

    return street, downloaded, empty, failed


def main():
    print("=" * 72)
    print("STRAATVIZIER - GERICHTE BACKFILL 2019")
    print("=" * 72)

    results = [backfill(*target) for target in TARGETS]

    print()
    print("=" * 72)
    print("SAMENVATTING")
    print("=" * 72)

    for street, downloaded, empty, failed in results:
        print()
        print(street)
        print(f"  records gedownload: {downloaded}")
        print(f"  periodes zonder data: {empty}")
        print(f"  mislukte periodes: {len(failed)}")
        for period in failed:
            print(f"    - {period}")


if __name__ == "__main__":
    main()
