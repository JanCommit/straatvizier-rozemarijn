from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_direction_config():
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
    labels = DIRECTION_CONFIG.get(street, {})

    if direction == "ab":
        return f'{labels.get("ab", "A → B")} (A → B)'

    if direction == "ba":
        return f'{labels.get("ba", "B → A")} (B → A)'

    return "Beide richtingen"


def sensor_history_label(street):
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
