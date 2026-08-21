import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# Configuratie
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "segments.yaml"

START_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

TELRAAM_API_URL = "https://telraam-api.net/v1/reports/traffic"

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


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


# ============================================================
# Config lezen
# ============================================================

def load_segments() -> list[dict]:
    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return config["segments"]


# ============================================================
# Supabase: straten en segmenten
# ============================================================

def get_or_create_street(street_name: str) -> int:
    response = (
        supabase
        .table("streets")
        .select("id")
        .eq("name", street_name)
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    response = (
        supabase
        .table("streets")
        .insert({
            "name": street_name,
        })
        .execute()
    )

    return response.data[0]["id"]


def get_or_create_segment(
    telraam_segment_id: int,
    street_id: int,
    street_name: str,
) -> int:

    response = (
        supabase
        .table("segments")
        .select("id")
        .eq("telraam_segment_id", telraam_segment_id)
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    response = (
        supabase
        .table("segments")
        .insert({
            "telraam_segment_id": telraam_segment_id,
            "street_id": street_id,
            "name": f"{street_name} - segment {telraam_segment_id}",
        })
        .execute()
    )

    return response.data[0]["id"]


# ============================================================
# Controleren of een maand al aanwezig is
# ============================================================

def month_has_data(
    database_segment_id: int,
    start: datetime,
    end: datetime,
) -> bool:

    response = (
        supabase
        .table("measurements")
        .select("id")
        .eq("segment_id", database_segment_id)
        .gte("measured_at", start.isoformat())
        .lt("measured_at", end.isoformat())
        .limit(1)
        .execute()
    )

    return bool(response.data)


# ============================================================
# Telraam API
# ============================================================

def fetch_telraam_period(
    telraam_segment_id: int,
    start: datetime,
    end: datetime,
) -> list[dict]:

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

            print()
            print(f"      Tijdelijke API-fout: {exc}")
            print(
                f"      Nieuwe poging over {wait_seconds}s "
                f"({attempt}/{max_attempts})"
            )

            time.sleep(wait_seconds)

    return []


# ============================================================
# Data transformeren
# ============================================================

def transform_record(
    record: dict,
    database_segment_id: int,
) -> dict:

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


# ============================================================
# Opslaan
# ============================================================

def save_records(records: list[dict]) -> None:
    if not records:
        return

    batch_size = 500

    for index in range(0, len(records), batch_size):
        batch = records[index:index + batch_size]

        (
            supabase
            .table("measurements")
            .upsert(
                batch,
                on_conflict="segment_id,measured_at",
            )
            .execute()
        )


# ============================================================
# Eén segment verwerken
# ============================================================

def backfill_segment(segment_config: dict) -> dict:
    telraam_segment_id = int(
        segment_config["telraam_segment_id"]
    )
    street_name = segment_config["street"]

    print()
    print("=" * 70)
    print(f"{street_name}")
    print(f"Telraam segment {telraam_segment_id}")
    print("=" * 70)

    street_id = get_or_create_street(street_name)

    database_segment_id = get_or_create_segment(
        telraam_segment_id,
        street_id,
        street_name,
    )

    current = START_DATE

    downloaded = 0
    skipped = 0
    empty = 0
    failed = []

    while current < END_DATE:

        period_end = min(
            current + relativedelta(months=1),
            END_DATE,
        )

        label = (
            f"{current:%Y-%m-%d} → "
            f"{period_end:%Y-%m-%d}"
        )

        # Reeds aanwezige historische maand?
        if month_has_data(
            database_segment_id,
            current,
            period_end,
        ):
            print(f"{label} ... reeds aanwezig → overslaan")
            skipped += 1
            current = period_end
            continue

        print(f"{label} ... ", end="", flush=True)

        try:
            raw_records = fetch_telraam_period(
                telraam_segment_id,
                current,
                period_end,
            )

            if not raw_records:
                print("geen data")
                empty += 1

            else:
                records = [
                    transform_record(
                        record,
                        database_segment_id,
                    )
                    for record in raw_records
                ]

                save_records(records)

                downloaded += len(records)

                print(
                    f"{len(records):5d} records opgeslagen ✓"
                )

        except Exception as exc:
            print("FOUT ✗")
            print(f"      {exc}")

            failed.append(label)

        time.sleep(1.1)

        current = period_end

    return {
        "street": street_name,
        "telraam_segment_id": telraam_segment_id,
        "downloaded": downloaded,
        "skipped_months": skipped,
        "empty_months": empty,
        "failed_periods": failed,
    }


# ============================================================
# Main
# ============================================================

def main():
    segments = load_segments()

    print("=" * 70)
    print("STRAATVIZIER - HISTORISCHE BACKFILL")
    print("=" * 70)
    print(f"Segmenten: {len(segments)}")
    print(f"Vanaf:     {START_DATE:%Y-%m-%d}")
    print(f"Tot:       {END_DATE:%Y-%m-%d}")

    results = []

    for segment in segments:
        result = backfill_segment(segment)
        results.append(result)

    print()
    print("=" * 70)
    print("SAMENVATTING")
    print("=" * 70)

    for result in results:
        print()
        print(
            f"{result['street']} "
            f"({result['telraam_segment_id']})"
        )
        print(
            f"  records gedownload: "
            f"{result['downloaded']}"
        )
        print(
            f"  maanden overgeslagen: "
            f"{result['skipped_months']}"
        )
        print(
            f"  maanden zonder data: "
            f"{result['empty_months']}"
        )
        print(
            f"  mislukte periodes: "
            f"{len(result['failed_periods'])}"
        )

        for period in result["failed_periods"]:
            print(f"    - {period}")


if __name__ == "__main__":
    main()