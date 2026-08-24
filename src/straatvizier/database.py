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


def get_measurement_bounds(
    segment_id: int,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    """
    Lees alleen de eerste en laatste meting van een segment.

    Hierdoor hoeft de volledige uurhistorie niet geladen te worden
    om de beschikbare periode te bepalen.
    """

    first_response = (
        supabase
        .table("measurements")
        .select("measured_at")
        .eq("segment_id", segment_id)
        .order("measured_at")
        .limit(1)
        .execute()
    )

    last_response = (
        supabase
        .table("measurements")
        .select("measured_at")
        .eq("segment_id", segment_id)
        .order("measured_at", desc=True)
        .limit(1)
        .execute()
    )

    if not first_response.data or not last_response.data:
        return None, None

    first = pd.to_datetime(
        first_response.data[0]["measured_at"],
        utc=True,
    )
    last = pd.to_datetime(
        last_response.data[0]["measured_at"],
        utc=True,
    )

    return first, last


def get_daily_traffic(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
) -> pd.DataFrame:
    """
    Laat Postgres dagtotalen berekenen.

    Alleen de dagelijkse aggregaten worden naar Streamlit gestuurd,
    niet de volledige uurhistorie.
    """

    page_size = 1000
    offset = 0
    all_rows = []

    while True:
        response = (
            supabase
            .rpc(
                "get_daily_traffic",
                {
                    "p_segment_id": segment_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_start_hour": start_hour,
                    "p_end_hour": end_hour,
                    "p_min_uptime": min_uptime,
                    "p_direction": direction,
                    "p_include_car": include_car,
                    "p_include_bike": include_bike,
                    "p_include_heavy": include_heavy,
                    "p_include_pedestrian": include_pedestrian,
                },
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        rows = response.data

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(all_rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "value",
                "hours",
                "avg_uptime",
            ]
        )

    df = df.rename(
        columns={
            "traffic_date": "date",
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"])
    df["hours"] = pd.to_numeric(df["hours"])
    df["avg_uptime"] = pd.to_numeric(df["avg_uptime"])

    return df


def get_hourly_traffic(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
) -> pd.DataFrame:
    """
    Lees gefilterde uurdata op aanvraag.

    Deze functie wordt alleen gebruikt wanneer de gebruiker
    expliciet de weergave 'Per uur' kiest.
    """

    page_size = 1000
    offset = 0
    all_rows = []

    while True:
        response = (
            supabase
            .rpc(
                "get_hourly_traffic",
                {
                    "p_segment_id": segment_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_start_hour": start_hour,
                    "p_end_hour": end_hour,
                    "p_min_uptime": min_uptime,
                    "p_direction": direction,
                    "p_include_car": include_car,
                    "p_include_bike": include_bike,
                    "p_include_heavy": include_heavy,
                    "p_include_pedestrian": include_pedestrian,
                },
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        rows = response.data

        if not rows:
            break

        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(all_rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "measured_at",
                "selected_traffic",
                "uptime",
            ]
        )

    df["measured_at"] = pd.to_datetime(
        df["measured_at"],
        utc=True,
    )
    df["selected_traffic"] = pd.to_numeric(
        df["selected_traffic"]
    )
    df["uptime"] = pd.to_numeric(df["uptime"])

    return df


def get_hour_profile(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
    direction: str,
    include_car: bool,
    include_bike: bool,
    include_heavy: bool,
    include_pedestrian: bool,
) -> pd.DataFrame:
    """
    Bereken het uurprofiel server-side.

    Hierdoor worden voor een profiel maximaal 24 rijen opgehaald.
    """

    response = (
        supabase
        .rpc(
            "get_hour_profile",
            {
                "p_segment_id": segment_id,
                "p_start_date": start_date,
                "p_end_date": end_date,
                "p_start_hour": start_hour,
                "p_end_hour": end_hour,
                "p_min_uptime": min_uptime,
                "p_direction": direction,
                "p_include_car": include_car,
                "p_include_bike": include_bike,
                "p_include_heavy": include_heavy,
                "p_include_pedestrian": include_pedestrian,
            },
        )
        .execute()
    )

    df = pd.DataFrame(response.data)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "hour",
                "avg_traffic",
            ]
        )

    df = df.rename(
        columns={
            "hour_of_day": "hour",
        }
    )

    df["hour"] = pd.to_numeric(df["hour"])
    df["avg_traffic"] = pd.to_numeric(
        df["avg_traffic"]
    )

    return df



# ============================================================
# Autosnelheid
# ============================================================

SPEED_BIN_COUNT = 25
SPEED_BIN_WIDTH = 5.0


def speed_percentile(
    histogram,
    percentile: float,
):
    """
    Bereken een percentiel uit het gewogen Telraam-histogram:
    0-5, 5-10, ..., 115-120, 120+ km/u.
    """
    if histogram is None or len(histogram) != SPEED_BIN_COUNT:
        return None

    values = [
        float(value or 0)
        for value in histogram
    ]

    total = sum(values)

    if total <= 0:
        return None

    target = total * percentile
    cumulative = 0.0

    for index, value in enumerate(values):
        previous = cumulative
        cumulative += value

        if cumulative >= target:
            if index == SPEED_BIN_COUNT - 1:
                return 120.0

            if value <= 0:
                return index * SPEED_BIN_WIDTH

            fraction = (
                target - previous
            ) / value

            return (
                index * SPEED_BIN_WIDTH
                + fraction * SPEED_BIN_WIDTH
            )

    return None


def _add_speed_percentiles(
    df: pd.DataFrame,
) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()

    result["v50"] = result["histogram"].apply(
        lambda hist: speed_percentile(hist, 0.50)
    )
    result["v85"] = result["histogram"].apply(
        lambda hist: speed_percentile(hist, 0.85)
    )
    result["v95"] = result["histogram"].apply(
        lambda hist: speed_percentile(hist, 0.95)
    )

    return result


def get_daily_speed(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
) -> pd.DataFrame:
    """
    Haal server-side geaggregeerde snelheidshistogrammen per dag op.
    """
    page_size = 1000
    offset = 0
    rows = []

    while True:
        response = (
            supabase
            .rpc(
                "get_daily_speed_histogram",
                {
                    "p_segment_id": segment_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_start_hour": start_hour,
                    "p_end_hour": end_hour,
                    "p_min_uptime": min_uptime,
                },
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        batch = response.data or []
        rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "histogram",
                "hours",
                "avg_uptime",
                "cars",
                "v50",
                "v85",
                "v95",
            ]
        )

    df["date"] = pd.to_datetime(
        df["traffic_date"]
    )
    df["hours"] = pd.to_numeric(
        df["hours"]
    )
    df["avg_uptime"] = pd.to_numeric(
        df["avg_uptime"]
    )
    df["cars"] = pd.to_numeric(
        df["cars"]
    )

    df = df.drop(
        columns=["traffic_date"]
    )

    return _add_speed_percentiles(df)


def get_hourly_speed(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
) -> pd.DataFrame:
    """
    Haal uurhistogrammen alleen op voor de expliciete 'Per uur'-weergave.
    """
    page_size = 1000
    offset = 0
    rows = []

    while True:
        response = (
            supabase
            .rpc(
                "get_hourly_speed_histogram",
                {
                    "p_segment_id": segment_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_start_hour": start_hour,
                    "p_end_hour": end_hour,
                    "p_min_uptime": min_uptime,
                },
            )
            .range(
                offset,
                offset + page_size - 1,
            )
            .execute()
        )

        batch = response.data or []
        rows.extend(batch)

        if len(batch) < page_size:
            break

        offset += page_size

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "measured_at",
                "histogram",
                "uptime",
                "cars",
                "v50",
                "v85",
                "v95",
            ]
        )

    df["measured_at"] = pd.to_datetime(
        df["measured_at"],
        utc=True,
    )
    df["uptime"] = pd.to_numeric(
        df["uptime"]
    )
    df["cars"] = pd.to_numeric(
        df["cars"]
    )

    return _add_speed_percentiles(df)


def get_speed_hour_profile(
    segment_id: int,
    start_date: str,
    end_date: str,
    start_hour: int,
    end_hour: int,
    min_uptime: float,
) -> pd.DataFrame:
    """
    Bereken het 24u-snelheidsprofiel server-side.
    """
    response = (
        supabase
        .rpc(
            "get_speed_hour_profile_histogram",
            {
                "p_segment_id": segment_id,
                "p_start_date": start_date,
                "p_end_date": end_date,
                "p_start_hour": start_hour,
                "p_end_hour": end_hour,
                "p_min_uptime": min_uptime,
            },
        )
        .execute()
    )

    df = pd.DataFrame(
        response.data or []
    )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "hour",
                "histogram",
                "cars",
                "v50",
                "v85",
                "v95",
            ]
        )

    df["hour"] = pd.to_numeric(
        df["hour_of_day"]
    )
    df["cars"] = pd.to_numeric(
        df["cars"]
    )

    df = df.drop(
        columns=["hour_of_day"]
    )

    return _add_speed_percentiles(df)


def sum_speed_histograms(
    histograms,
):
    """
    Sommeer reeds gewogen histogrammen.
    """
    total = [0.0] * SPEED_BIN_COUNT
    found = False

    for histogram in histograms:
        if histogram is None or len(histogram) != SPEED_BIN_COUNT:
            continue

        values = [
            float(value or 0)
            for value in histogram
        ]

        if sum(values) <= 0:
            continue

        found = True

        total = [
            left + right
            for left, right in zip(
                total,
                values,
            )
        ]

    return (
        total
        if found
        else None
    )


def aggregate_speed_period(
    daily_df: pd.DataFrame,
    period: str,
) -> pd.DataFrame:
    """
    Aggregeer geldige daghistogrammen naar week, maand of jaar.
    """
    if daily_df.empty:
        return pd.DataFrame()

    data = daily_df.copy()

    if period == "week":
        data["period"] = (
            data["date"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
    elif period == "month":
        data["period"] = (
            data["date"]
            .dt.to_period("M")
            .dt.start_time
        )
    elif period == "year":
        data["period"] = (
            data["date"]
            .dt.to_period("Y")
            .dt.start_time
        )
    else:
        raise ValueError(
            f"Onbekende periode: {period}"
        )

    rows = []

    for period_value, group in data.groupby(
        "period"
    ):
        histogram = sum_speed_histograms(
            group["histogram"]
        )

        if histogram is None:
            continue

        rows.append({
            period: period_value,
            "histogram": histogram,
            "days": len(group),
            "cars": group["cars"].sum(),
        })

    return _add_speed_percentiles(
        pd.DataFrame(rows)
    )


def get_speed_week_profile(
    daily_df: pd.DataFrame,
) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame()

    data = daily_df.copy()
    data["weekday"] = (
        data["date"].dt.weekday
    )

    rows = []

    for weekday, group in data.groupby(
        "weekday"
    ):
        histogram = sum_speed_histograms(
            group["histogram"]
        )

        if histogram is not None:
            rows.append({
                "weekday": weekday,
                "histogram": histogram,
                "cars": group["cars"].sum(),
            })

    return _add_speed_percentiles(
        pd.DataFrame(rows)
    )


def get_speed_year_profile(
    daily_df: pd.DataFrame,
) -> pd.DataFrame:
    if daily_df.empty:
        return pd.DataFrame()

    data = daily_df.copy()
    data["month_number"] = (
        data["date"].dt.month
    )

    rows = []

    for month_number, group in data.groupby(
        "month_number"
    ):
        histogram = sum_speed_histograms(
            group["histogram"]
        )

        if histogram is not None:
            rows.append({
                "month_number":
                    month_number,
                "histogram":
                    histogram,
                "cars":
                    group["cars"].sum(),
            })

    return _add_speed_percentiles(
        pd.DataFrame(rows)
    )
