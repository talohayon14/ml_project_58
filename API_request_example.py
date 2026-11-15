"""Simple Open-Meteo request-loop example.

This is one possible collection strategy. Students may divide the required
locations and dates into requests differently, provided that the resulting
dataset follows the project data contract.
"""

import json
import time
from collections import deque
from pathlib import Path

import requests


ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_LIMIT = 5_000
DAILY_LIMIT = 10_000

LOCATIONS = {
    "london": (51.5074, -0.1278),
    "berlin": (52.5200, 13.4050),
    "new_york": (40.7128, -74.0060),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "vancouver": (49.2827, -123.1207),
}

DAILY_VARIABLES = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_mean",
    "precipitation_sum",
    "rain_sum",
    "precipitation_hours",
    "wind_speed_10m_max",
    "wind_direction_10m_dominant",
]


def wait_for_rate_limits(hourly_times: deque, daily_times: deque) -> None:
    """Wait before a request would exceed an hourly or daily limit."""
    while True:
        now = time.time()
        while hourly_times and now - hourly_times[0] >= 60 * 60:
            hourly_times.popleft()
        while daily_times and now - daily_times[0] >= 24 * 60 * 60:
            daily_times.popleft()

        waits = []
        if len(hourly_times) >= HOURLY_LIMIT:
            waits.append(60 * 60 - (now - hourly_times[0]))
        if len(daily_times) >= DAILY_LIMIT:
            waits.append(24 * 60 * 60 - (now - daily_times[0]))
        if not waits:
            return
        time.sleep(max(waits) + 1)


def collect() -> None:
    output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    hourly_times: deque[float] = deque()
    daily_times: deque[float] = deque()

    with requests.Session() as session:
        for location, (latitude, longitude) in LOCATIONS.items():
            wait_for_rate_limits(hourly_times, daily_times)
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": "auto",
            }
            response = session.get(ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error") is True or "daily" not in payload:
                raise RuntimeError(f"Invalid response for {location}: {payload}")

            request_time = time.time()
            hourly_times.append(request_time)
            daily_times.append(request_time)

            output = output_dir / f"{location}.json"
            output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved {location} to {output}")
            time.sleep(0.25)


if __name__ == "__main__":
    collect()
