"""Controleer handmatig een rechtstreekse Telraam API-oproep voor een voorbeeldsegment.

Diagnostisch script voor API-key, requestformaat en bronrespons; het schrijft geen
gegevens naar Supabase."""

import os

import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("TELRAAM_API_KEY")

if not API_KEY:
    raise RuntimeError("TELRAAM_API_KEY niet gevonden in .env")

url = "https://telraam-api.net/v1/reports/traffic"

# Voorlopig een voorbeeldsegment uit de Telraam-documentatie.
# Straks vervangen we dit door onze eigen segmenten.
payload = {
    "id": "155073",
    "time_start": "2020-01-01 00:00:00Z",
    "time_end": "2020-03-31 23:59:59Z",
    "level": "segments",
    "format": "per-hour",
}

headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json",
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=30,
)

print("HTTP status:", response.status_code)

if response.ok:
    data = response.json()
    print("API-key werkt.")
    print("Aantal records:", len(data.get("report", [])))

    if data.get("report"):
        print("\nEerste record:")
        print(data["report"][0])
else:
    print("API-aanroep mislukt:")
    print(response.text)