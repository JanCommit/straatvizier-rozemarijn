"""Inspecteer camerageschiedenis voor de segmenten uit ``config/segments.yaml``.

Vergelijkt de Telraam-camera-instanties met de geconfigureerde sensorhistoriek en
is bedoeld als diagnostische controle bij sensorwissels of onduidelijke meetperiodes."""

import os
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "segments.yaml"

load_dotenv(PROJECT_ROOT / ".env")

TELRAAM_API_KEY = os.getenv("TELRAAM_API_KEY")

if not TELRAAM_API_KEY:
    raise RuntimeError("TELRAAM_API_KEY ontbreekt in .env")

if not CONFIG_PATH.exists():
    raise RuntimeError(f"Configuratiebestand niet gevonden: {CONFIG_PATH}")


API_BASE = "https://telraam-api.net/v1/cameras/segment"
REQUEST_DELAY = 1.1
MAX_RETRIES = 5


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fmt(value):
    if value is None:
        return "—"
    return value.strftime("%d/%m/%Y")


def hardware_label(version):
    if version == 1:
        return "S1"
    if version == 2:
        return "S2"
    return f"hardware_version={version}"


def fetch_instances(segment_id):
    url = f"{API_BASE}/{segment_id}"
    headers = {"X-Api-Key": TELRAAM_API_KEY}

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            payload = response.json()
            return payload.get("camera", [])

        if response.status_code == 429 and attempt < MAX_RETRIES:
            wait = max(REQUEST_DELAY, attempt * 2)
            print(
                f"429 Too Many Requests voor segment {segment_id}; "
                f"{wait:.1f}s wachten..."
            )
            time.sleep(wait)
            continue

        raise RuntimeError(
            f"Telraam API fout voor segment {segment_id}: "
            f"{response.status_code} {response.text}"
        )

    return []


def active_period(instance):
    """
    Gebruik first_data_package/last_data_package als echte dataperiode.
    Als die ontbreken, val terug op time_added/time_end.
    """
    start = (
        parse_dt(instance.get("first_data_package"))
        or parse_dt(instance.get("time_added"))
    )

    end = (
        parse_dt(instance.get("last_data_package"))
        or parse_dt(instance.get("time_end"))
    )

    if instance.get("status") == "active" and instance.get("time_end") is None:
        end = None

    return start, end


def merge_periods(periods):
    """
    Voeg overlappende/aansluitende periodes van hetzelfde hardwaretype samen.
    Een gat van maximaal 1 dag wordt als aansluitend beschouwd.
    """
    periods = sorted(
        [p for p in periods if p[0] is not None],
        key=lambda p: p[0],
    )

    if not periods:
        return []

    merged = []

    for start, end in periods:
        if not merged:
            merged.append([start, end])
            continue

        prev_start, prev_end = merged[-1]

        # Open actieve periode blijft open.
        if prev_end is None:
            continue

        # Nieuwe open periode die aansluit/overlapt.
        if end is None:
            if start <= prev_end:
                merged[-1][1] = None
            else:
                merged.append([start, None])
            continue

        # Overlap of maximaal één dag tussenruimte.
        gap_seconds = (start - prev_end).total_seconds()

        if gap_seconds <= 86400:
            if end > prev_end:
                merged[-1][1] = end
        else:
            merged.append([start, end])

    return [tuple(item) for item in merged]


def summarize_instances(instances):
    by_hardware = {}

    for instance in instances:
        version = instance.get("hardware_version")
        start, end = active_period(instance)

        by_hardware.setdefault(version, []).append(
            (start, end)
        )

    summary = {}

    for version, periods in by_hardware.items():
        summary[version] = merge_periods(periods)

    return summary


def main():
    config = yaml.safe_load(
        CONFIG_PATH.read_text(encoding="utf-8")
    ) or {}

    segments = config.get("segments", [])

    print("=" * 78)
    print("TELRAAM SENSORHISTORIE")
    print("=" * 78)
    print()
    print(
        "Interpretatie: hardware_version 1 = S1, "
        "hardware_version 2 = S2."
    )
    print(
        "Periodes hieronder gebruiken waar mogelijk "
        "first_data_package en last_data_package."
    )
    print()

    for index, segment in enumerate(segments):
        street = segment["street"]
        segment_id = segment["telraam_segment_id"]

        if index:
            time.sleep(REQUEST_DELAY)

        print("=" * 78)
        print(f"{street} ({segment_id})")
        print("=" * 78)

        try:
            instances = fetch_instances(segment_id)
        except Exception as exc:
            print(f"FOUT: {exc}")
            print()
            continue

        if not instances:
            print("Geen camera-instances gevonden.")
            print()
            continue

        # Ruwe instances eerst, zodat we uitzonderingen kunnen controleren.
        for instance in sorted(
            instances,
            key=lambda item: (
                parse_dt(item.get("first_data_package"))
                or parse_dt(item.get("time_added"))
                or datetime.min.replace(tzinfo=None)
            ),
        ):
            version = instance.get("hardware_version")
            start, end = active_period(instance)

            print(
                f"instance {instance.get('instance_id')} | "
                f"{hardware_label(version)} | "
                f"status={instance.get('status')} | "
                f"data {fmt(start)} → {fmt(end) if end else 'heden'}"
            )

        print()
        print("SAMENGEVAT:")

        summary = summarize_instances(instances)

        for version in sorted(
            summary,
            key=lambda value: (
                999 if value is None else value
            ),
        ):
            label = hardware_label(version)

            for start, end in summary[version]:
                if end is None:
                    print(
                        f"  {label}: vanaf {fmt(start)}"
                    )
                elif start.date() == end.date():
                    print(
                        f"  {label}: {fmt(start)}"
                    )
                else:
                    print(
                        f"  {label}: {fmt(start)} t.e.m. {fmt(end)}"
                    )

        print()

    print("=" * 78)
    print("KLAAR")
    print("=" * 78)


if __name__ == "__main__":
    main()

