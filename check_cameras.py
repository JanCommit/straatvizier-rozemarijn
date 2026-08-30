"""Controleer via de Telraam API welke camera-instanties aan enkele segmenten gekoppeld zijn.

Diagnostisch hulpscript; schrijft niets naar Supabase en bevat bewust een vaste lijst
segmenten om sensorwissels of camerageschiedenis te inspecteren."""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TELRAAM_API_KEY")

segments = {
    "Papagaaistraat": 9000008840,
    "Coupure Links": 155401,
    "Wispelbergstraat": 9000006262,
    "Iepenstraat": 9000011803,
    "Rooigemlaan": 9000007115,
}

headers = {
    "X-Api-Key": api_key,
}

for street, segment_id in segments.items():
    url = (
        f"https://telraam-api.net/v1/cameras/"
        f"segment/{segment_id}"
    )

    for attempt in range(5):
        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        if response.status_code != 429:
            break

        print(
            f"{street}: rate limit, "
            "20 seconden wachten..."
        )
        time.sleep(20)

    print("\n" + "=" * 70)
    print(street, segment_id)
    print("=" * 70)

    if response.status_code != 200:
        print(
            "FOUT:",
            response.status_code,
            response.text,
        )
        continue

    cameras = response.json().get(
        "camera",
        [],
    )

    for camera in cameras:
        print({
            "instance_id":
                camera.get("instance_id"),
            "hardware_version":
                camera.get("hardware_version"),
            "status":
                camera.get("status"),
            "time_added":
                camera.get("time_added"),
            "first_data_package":
                camera.get("first_data_package"),
            "last_data_package":
                camera.get("last_data_package"),
            "time_end":
                camera.get("time_end"),
        })

    # Even wachten voor de volgende straat
    time.sleep(5)
