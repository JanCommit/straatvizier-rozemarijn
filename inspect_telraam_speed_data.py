"""Inspecteer ruwe snelheidsvelden uit één Telraam API-respons.

Diagnostisch hulpscript met een vast segment en tijdsvenster. Gebruik dit om de
beschikbare histogram- en snelheidsvelden rechtstreeks in de brondata te bekijken."""

import os
import json
import requests

from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("TELRAAM_API_KEY")

SEGMENT_ID = 155073  # Rozemarijnstraat

url = "https://telraam-api.net/v1/reports/traffic"

headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
}

payload = {
    "level": "segments",
    "format": "per-hour",
    "id": SEGMENT_ID,
    "time_start": "2026-08-20 00:00:00Z",
    "time_end": "2026-08-21 00:00:00Z",
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=30,
)

print("HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit

data = response.json()

reports = data.get("report", [])

print("Aantal uurrecords:", len(reports))

if not reports:
    print("Geen records ontvangen.")
    raise SystemExit

print("\nBeschikbare velden in eerste record:")
print("-------------------------------------")

for key in sorted(reports[0].keys()):
    print(key)

print("\nSnelheidsvelden:")
print("----------------")

speed_keys = [
    key
    for key in reports[0].keys()
    if "speed" in key.lower()
]

for key in speed_keys:
    print(f"\n{key}:")
    print(
        json.dumps(
            reports[0].get(key),
            indent=2,
        )
    )

print("\nAlle uurrecords met snelheid:")
print("-----------------------------")

for report in reports:
    print(
        "\n",
        report.get("date"),
        report.get("date_start"),
        report.get("time"),
    )

    for key in speed_keys:
        print(
            f"{key}:",
            report.get(key),
        )
