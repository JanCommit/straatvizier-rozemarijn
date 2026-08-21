import os
import time
from datetime import datetime, timezone

import requests
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("TELRAAM_API_KEY")

if not API_KEY:
    raise RuntimeError("TELRAAM_API_KEY niet gevonden in .env")

API_URL = "https://telraam-api.net/v1/reports/traffic"

# Eerste echte StraatVizier-segment
SEGMENT_ID = 155073
STREET_NAME = "Rozemarijnstraat"

# We weten inmiddels dat er in 2020 al data is.
START_DATE = datetime(2020, 1, 1, tzinfo=timezone.utc)

# Tot vandaag.
END_DATE = datetime.now(timezone.utc)


def fetch_period(start: datetime, end: datetime) -> list[dict]:
    payload = {
        "id": str(SEGMENT_ID),
        "time_start": start.strftime("%Y-%m-%d %H:%M:%SZ"),
        "time_end": end.strftime("%Y-%m-%d %H:%M:%SZ"),
        "level": "segments",
        "format": "per-hour",
    }

    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
    }

    max_attempts = 4

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                API_URL,
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

            retryable = status_code in {500, 502, 503, 504} or status_code is None

            if not retryable or attempt == max_attempts:
                raise

            wait_seconds = attempt * 5

            print(
                f"\n  tijdelijke API-fout ({exc}), "
                f"poging {attempt}/{max_attempts}. "
                f"Opnieuw over {wait_seconds}s...",
                flush=True,
            )

            time.sleep(wait_seconds)

    return []


def main():
    print(f"Historiek onderzoeken voor {STREET_NAME}")
    print(f"Segment: {SEGMENT_ID}")
    print("-" * 70)

    current = START_DATE

    total_records = 0
    first_record = None
    last_record = None

    while current < END_DATE:
        # We gebruiken blokken van 2 maanden.
        # Daarmee blijven we veilig onder de API-limiet van 3 maanden.
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
            records = fetch_period(current, period_end)

        except requests.RequestException as exc:
            print(f"FOUT: {exc}")
            current = period_end
            time.sleep(2)
            continue

        count = len(records)
        total_records += count

        if records:
            dates = [record["date"] for record in records]

            period_first = min(dates)
            period_last = max(dates)

            if first_record is None or period_first < first_record:
                first_record = period_first

            if last_record is None or period_last > last_record:
                last_record = period_last

            uptimes = [
                record["uptime"]
                for record in records
                if record.get("uptime") is not None
            ]

            average_uptime = (
                sum(uptimes) / len(uptimes)
                if uptimes
                else None
            )

            if average_uptime is not None:
                print(
                    f"{count:5d} records | "
                    f"gem. uptime {average_uptime:.1%}"
                )
            else:
                print(f"{count:5d} records | uptime onbekend")

        else:
            print("0 records")

        # Telraam heeft rate limits.
        # We wachten bewust iets langer dan één seconde.
        time.sleep(1.1)

        current = period_end

    print()
    print("=" * 70)
    print("RESULTAAT")
    print("=" * 70)
    print(f"Straat:          {STREET_NAME}")
    print(f"Segment:         {SEGMENT_ID}")
    print(f"Totaal records:  {total_records}")
    print(f"Eerste meting:   {first_record}")
    print(f"Laatste meting:  {last_record}")


if __name__ == "__main__":
    main()