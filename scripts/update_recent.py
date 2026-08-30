"""Werk de recente Telraam-data van alle geconfigureerde segmenten bij in Supabase.

Dit is het reguliere updatescript dat ook door GitHub Actions wordt gebruikt. Het
haalt bewust enkele dagen overlap opnieuw op zodat late of gecorrigeerde brondata
via UPSERT kan worden bijgewerkt."""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# Configuratie
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "segments.yaml"

TELRAAM_API_URL = "https://telraam-api.net/v1/reports/traffic"

# We halen bewust een overlap op zodat late/corrigerende Telraam-data
# via UPSERT opnieuw wordt bijgewerkt.
LOOKBACK_DAYS = 7

load_dotenv(PROJECT_ROOT / ".env")

TELRAAM_API_KEY = os.getenv("TELRAAM_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not TELRAAM_API_KEY:
    raise RuntimeError(
        "TELRAAM_API_KEY ontbreekt. "
        "Lokaal: zet hem in .env. "
        "GitHub Actions: voeg hem toe als repository secret."
    )

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL ontbreekt. "
        "Lokaal: zet hem in .env. "
        "GitHub Actions: voeg hem toe als repository secret."
    )

if not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "SUPABASE_SECRET_KEY ontbreekt. "
        "Lokaal: zet hem in .env. "
        "GitHub Actions: voeg hem toe als repository secret."
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


# ============================================================
# Config lezen
# ============================================================

def load_segments() -> list[dict]:
    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        config = yaml.safe_load(file)

    return config["segments"]


# ============================================================
# Supabase: straten en segmenten
# ============================================================

def get_or_create_street(
    street_name: str,
) -> int:
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
        .eq(
            "telraam_segment_id",
            telraam_segment_id,
        )
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    response = (
        supabase
        .table("segments")
        .insert({
            "telraam_segment_id":
                telraam_segment_id,
            "street_id":
                street_id,
            "name":
                f"{street_name} - "
                f"segment {telraam_segment_id}",
        })
        .execute()
    )

    return response.data[0]["id"]


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
        "time_start":
            start.strftime(
                "%Y-%m-%d %H:%M:%SZ"
            ),
        "time_end":
            end.strftime(
                "%Y-%m-%d %H:%M:%SZ"
            ),
        "level": "segments",
        "format": "per-hour",
    }

    headers = {
        "X-Api-Key": TELRAAM_API_KEY,
        "Content-Type": "application/json",
    }

    max_attempts = 5

    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            response = requests.post(
                TELRAAM_API_URL,
                headers=headers,
                json=payload,
                timeout=90,
            )

            response.raise_for_status()

            return (
                response
                .json()
                .get("report", [])
            )

        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.HTTPError,
        ) as exc:
            status_code = (
                exc.response.status_code
                if (
                    isinstance(
                        exc,
                        requests.HTTPError,
                    )
                    and exc.response
                    is not None
                )
                else None
            )

            retryable = (
                status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                or status_code is None
            )

            if (
                not retryable
                or attempt == max_attempts
            ):
                raise

            wait_seconds = (
                attempt * 5
            )

            print()
            print(
                f"    Tijdelijke API-fout: "
                f"{exc}"
            )
            print(
                f"    Nieuwe poging over "
                f"{wait_seconds}s "
                f"({attempt}/{max_attempts})"
            )

            time.sleep(
                wait_seconds
            )

    return []


# ============================================================
# Data transformeren
# ============================================================

def transform_record(
    record: dict,
    database_segment_id: int,
) -> dict:
    return {
        "segment_id":
            database_segment_id,
        "measured_at":
            record["date"],

        "uptime":
            record.get("uptime"),

        "heavy":
            record.get("heavy"),
        "car":
            record.get("car"),
        "bike":
            record.get("bike"),
        "pedestrian":
            record.get("pedestrian"),
        "night":
            record.get("night"),

        "heavy_left":
            record.get("heavy_lft"),
        "heavy_right":
            record.get("heavy_rgt"),

        "car_left":
            record.get("car_lft"),
        "car_right":
            record.get("car_rgt"),

        "bike_left":
            record.get("bike_lft"),
        "bike_right":
            record.get("bike_rgt"),

        "pedestrian_left":
            record.get("pedestrian_lft"),
        "pedestrian_right":
            record.get("pedestrian_rgt"),

        "night_left":
            record.get("night_lft"),
        "night_right":
            record.get("night_rgt"),


        "v85": record.get("v85"),
        "car_speed_hist_0to120plus": record.get("car_speed_hist_0to120plus"),

        "direction":
            record.get("direction"),
        "timezone":
            record.get("timezone"),
    }


# ============================================================
# Opslaan
# ============================================================

def save_records(
    records: list[dict],
) -> None:
    if not records:
        return

    batch_size = 500

    for index in range(
        0,
        len(records),
        batch_size,
    ):
        batch = records[
            index:index + batch_size
        ]

        (
            supabase
            .table("measurements")
            .upsert(
                batch,
                on_conflict=(
                    "segment_id,"
                    "measured_at"
                ),
            )
            .execute()
        )


# ============================================================
# Eén segment updaten
# ============================================================

def update_segment(
    segment_config: dict,
    start: datetime,
    end: datetime,
) -> dict:
    telraam_segment_id = int(
        segment_config[
            "telraam_segment_id"
        ]
    )

    street_name = (
        segment_config["street"]
    )

    print()
    print("=" * 70)
    print(street_name)
    print(
        f"Telraam segment "
        f"{telraam_segment_id}"
    )
    print(
        f"{start:%Y-%m-%d %H:%M} UTC "
        f"→ "
        f"{end:%Y-%m-%d %H:%M} UTC"
    )
    print("=" * 70)

    street_id = get_or_create_street(
        street_name
    )

    database_segment_id = (
        get_or_create_segment(
            telraam_segment_id,
            street_id,
            street_name,
        )
    )

    raw_records = fetch_telraam_period(
        telraam_segment_id,
        start,
        end,
    )

    if not raw_records:
        print("Geen data ontvangen.")
        return {
            "street":
                street_name,
            "downloaded":
                0,
            "saved":
                0,
        }

    records = [
        transform_record(
            record,
            database_segment_id,
        )
        for record in raw_records
    ]

    save_records(
        records
    )

    print(
        f"{len(records)} records "
        f"opgehaald en ge-upsert ✓"
    )

    return {
        "street":
            street_name,
        "downloaded":
            len(raw_records),
        "saved":
            len(records),
    }


# ============================================================
# Main
# ============================================================

def main():
    now = datetime.now(
        timezone.utc
    )

    start = (
        now
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )

    segments = load_segments()

    print("=" * 70)
    print(
        "STRAATVIZIER - "
        "RECENTE DATA-UPDATE"
    )
    print("=" * 70)
    print(
        f"Segmenten: {len(segments)}"
    )
    print(
        f"Lookback:  {LOOKBACK_DAYS} dagen"
    )
    print(
        f"Vanaf:     "
        f"{start:%Y-%m-%d %H:%M} UTC"
    )
    print(
        f"Tot:       "
        f"{now:%Y-%m-%d %H:%M} UTC"
    )

    results = []
    failed = []

    for segment in segments:
        try:
            result = update_segment(
                segment,
                start,
                now,
            )

            results.append(
                result
            )

        except Exception as exc:
            street_name = (
                segment.get(
                    "street",
                    "onbekend",
                )
            )

            print()
            print(
                f"FOUT bij "
                f"{street_name}: "
                f"{exc}"
            )

            failed.append({
                "street":
                    street_name,
                "error":
                    str(exc),
            })

        # Telraam niet onnodig snel
        # achter elkaar aanspreken.
        time.sleep(1.1)

    print()
    print("=" * 70)
    print("SAMENVATTING")
    print("=" * 70)

    for result in results:
        print(
            f"{result['street']}: "
            f"{result['saved']} "
            f"records ge-upsert"
        )

    if failed:
        print()
        print(
            f"Mislukte straten: "
            f"{len(failed)}"
        )

        for item in failed:
            print(
                f"  - "
                f"{item['street']}: "
                f"{item['error']}"
            )

        # Laat GitHub Actions falen
        # als minstens één segment
        # niet kon worden bijgewerkt.
        raise SystemExit(1)

    print()
    print(
        "Update succesvol afgerond ✓"
    )


if __name__ == "__main__":
    main()
