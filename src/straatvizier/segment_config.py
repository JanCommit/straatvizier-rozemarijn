"""Lees straatgebonden richtinglabels en sensorhistoriek uit segments.yaml."""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_direction_config():
    """Lees per Telraam-segment richtinglabels en optionele sensorhistoriek."""
    config_path = PROJECT_ROOT / "config" / "segments.yaml"

    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    return {
        item["street"]: {
            "ab": item.get("direction_ab_label", "A → B"),
            "ba": item.get("direction_ba_label", "B → A"),
            "sensor_history": item.get("sensor_history", []),
        }
        for item in raw.get("segments", [])
    }


DIRECTION_CONFIG = load_direction_config()


def direction_label(street, direction):
    """Geef het leesbare, straatafhankelijke label voor een interne richting."""
    labels = DIRECTION_CONFIG.get(street, {})

    if direction == "ab":
        return f'{labels.get("ab", "A → B")} (A → B)'

    if direction == "ba":
        return f'{labels.get("ba", "B → A")} (B → A)'

    return "Beide richtingen"


def sensor_history_label(street):
    """Formatteer de bekende sensorperioden van een segment voor de UI."""
    history = DIRECTION_CONFIG.get(
        street,
        {},
    ).get(
        "sensor_history",
        [],
    )

    if not history:
        return None

    parts = []

    for item in history:
        sensor = item.get("sensor")
        start = item.get("start")
        end = item.get("end")

        if start and end:
            parts.append(
                f"{sensor}: {start}–{end}"
            )
        elif start:
            parts.append(
                f"{sensor}: vanaf {start}"
            )

    return " · ".join(parts) if parts else None

from datetime import datetime

def sensor_start_date(street, sensor_type):
    """Geef de startdatum van een sensortype voor een straat."""
    history = DIRECTION_CONFIG.get(
        street,
        {},
    ).get(
        "sensor_history",
        [],
    )

    for item in history:
        if item.get("sensor") == sensor_type:
            start = item.get("start")

            if start:
                return datetime.strptime(
                    start,
                    "%d/%m/%Y",
                ).date()

    return None

NIGHT_COUNTS_START_DATE = datetime.strptime(
    "15/06/2024",
    "%d/%m/%Y",
).date()


def night_counts_start_date(street):
    """Geef de effectieve startdatum voor S2-nachttellingen."""
    s2_start = sensor_start_date(street, "S2")

    if s2_start is None:
        return None

    return max(
        s2_start,
        NIGHT_COUNTS_START_DATE,
    )