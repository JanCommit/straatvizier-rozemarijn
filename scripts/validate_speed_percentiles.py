"""Valideer histogram-afgeleide snelheidspercentielen tegen opgeslagen Telraam-data.

Diagnostisch validatiescript dat steekproeven uit Supabase gebruikt om de gekozen
interpolatiemethode voor onder meer V85 te controleren."""

import os
import random
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL ontbreekt in .env")

if not SUPABASE_SECRET_KEY:
    raise RuntimeError("SUPABASE_SECRET_KEY ontbreekt in .env")


supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY,
)


def percentile_from_histogram(histogram, percentile: float):
    """
    Bereken een snelheidspercentiel uit car_speed_hist_0to120plus.

    Bins:
    0-5, 5-10, ..., 115-120, 120+ km/u.

    Voor de eerste 24 bins interpoleren we lineair binnen de bin.
    Voor de open 120+ bin geven we 120 km/u terug als ondergrens.
    """

    if not histogram or len(histogram) != 25:
        return None

    values = [float(value or 0) for value in histogram]
    total = sum(values)

    if total <= 0:
        return None

    target = total * percentile
    cumulative = 0.0

    for index, value in enumerate(values):
        previous = cumulative
        cumulative += value

        if cumulative >= target:
            if index == 24:
                return 120.0

            lower = index * 5.0

            if value <= 0:
                return lower

            fraction_inside_bin = (target - previous) / value
            return lower + fraction_inside_bin * 5.0

    return None


def main():
    response = (
        supabase
        .table("measurements")
        .select(
            "id, measured_at, segment_id, car, v85, "
            "car_speed_hist_0to120plus"
        )
        .not_.is_("v85", "null")
        .not_.is_("car_speed_hist_0to120plus", "null")
        .limit(5000)
        .execute()
    )

    rows = response.data or []

    rows = [
        row
        for row in rows
        if (
            row.get("car_speed_hist_0to120plus")
            and sum(
                float(value or 0)
                for value in row["car_speed_hist_0to120plus"]
            ) > 0
        )
    ]

    print(f"Bruikbare records opgehaald: {len(rows)}")

    if not rows:
        return

    sample = random.sample(
        rows,
        min(1000, len(rows)),
    )

    differences = []

    print()
    print("Voorbeelden")
    print("=" * 90)

    shown = 0

    for row in sample:
        calculated_v85 = percentile_from_histogram(
            row["car_speed_hist_0to120plus"],
            0.85,
        )

        telraam_v85 = row.get("v85")

        if calculated_v85 is None or telraam_v85 is None:
            continue

        telraam_v85 = float(telraam_v85)
        difference = calculated_v85 - telraam_v85

        differences.append({
            "difference": difference,
            "absolute_difference": abs(difference),
            "calculated": calculated_v85,
            "telraam": telraam_v85,
            "row": row,
        })

        if shown < 20:
            car = row.get("car")
            car_text = "—" if car is None else f"{float(car):.1f}"

            print(
                f'{row["measured_at"]} | '
                f'car={car_text} | '
                f'Telraam V85={telraam_v85:.2f} | '
                f'berekend={calculated_v85:.2f} | '
                f'verschil={difference:+.2f}'
            )
            shown += 1

    if not differences:
        print("Geen vergelijkbare records.")
        return

    absolute = [item["absolute_difference"] for item in differences]
    signed = [item["difference"] for item in differences]
    n = len(absolute)

    print()
    print("=" * 90)
    print("SAMENVATTING")
    print("=" * 90)
    print(f"Aantal vergeleken records: {n}")
    print(
        "Gemiddeld absoluut verschil: "
        f"{sum(absolute) / n:.3f} km/u"
    )
    print(
        "Gemiddeld verschil: "
        f"{sum(signed) / n:+.3f} km/u"
    )
    print(
        "Maximum absoluut verschil: "
        f"{max(absolute):.3f} km/u"
    )

    print()
    print(
        f"≤ 0.5 km/u: "
        f"{sum(x <= 0.5 for x in absolute) / n * 100:.1f}%"
    )
    print(
        f"≤ 1.0 km/u: "
        f"{sum(x <= 1.0 for x in absolute) / n * 100:.1f}%"
    )
    print(
        f"≤ 2.5 km/u: "
        f"{sum(x <= 2.5 for x in absolute) / n * 100:.1f}%"
    )

    print()
    print("10 grootste afwijkingen")
    print("=" * 90)

    worst = sorted(
        differences,
        key=lambda item: item["absolute_difference"],
        reverse=True,
    )[:10]

    for item in worst:
        row = item["row"]
        car = row.get("car")
        car_text = "—" if car is None else f"{float(car):.1f}"

        print(
            f'{row["measured_at"]} | '
            f'segment={row["segment_id"]} | '
            f'car={car_text} | '
            f'Telraam={item["telraam"]:.2f} | '
            f'berekend={item["calculated"]:.2f} | '
            f'verschil={item["difference"]:+.2f}'
        )


if __name__ == "__main__":
    main()

