"""Data collection from the Open-Meteo Historical Weather API.

Downloads daily weather variables for six cities, one request per
(city, year), and stores every response as a raw JSON file under
data/raw/ exactly as it was received from the API.

Features required by the project:
  * request counting with waiting before exceeding the hourly/daily limits
  * retry with back-off on HTTP 429 and 5xx (and on network errors)
  * stop on HTTP 400 and print the server's reason so the request can be fixed
  * caching: files that already exist are never downloaded again

Run:  python data_collection.py
"""

import json
import sys
import time
from collections import deque
from datetime import date, timedelta
from pathlib import Path

import requests


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_LIMIT = 5_000          # max requests per hour
DAILY_LIMIT = 10_000          # max requests per 24 hours

START_YEAR = 2010
# The archive lags a few days behind real time, so stop one week before today.
END_DATE = date.today() - timedelta(days=7)

OUTPUT_DIR = Path("data/raw")

MAX_RETRIES = 5               # attempts per request on 429 / 5xx / network error
BACKOFF_BASE = 2              # wait 2, 4, 8, 16, 32 seconds between attempts
PAUSE_BETWEEN_REQUESTS = 0.25 # polite pause after a successful request

LOCATIONS = {
    "london":    (51.5074,   -0.1278),
    "new_york":  (40.7128,  -74.0060),
    "sydney":   (-33.8688,  151.2093),
    "berlin":    (52.5200,   13.4050),
    "tokyo":     (35.6762,  139.6503),
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


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Counts requests in sliding windows of 1 hour and 24 hours.

    Call wait() before sending a request and record() right after sending it
    (whether or not it succeeded - the server counts every request).
    """

    def __init__(self, hourly_limit: int = HOURLY_LIMIT, daily_limit: int = DAILY_LIMIT):
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.hourly_times: deque[float] = deque()
        self.daily_times: deque[float] = deque()
        self.total = 0

    def _drop_old(self, now: float) -> None:
        while self.hourly_times and now - self.hourly_times[0] >= 60 * 60:
            self.hourly_times.popleft()
        while self.daily_times and now - self.daily_times[0] >= 24 * 60 * 60:
            self.daily_times.popleft()

    def wait(self) -> None:
        """Block until one more request can be sent without exceeding a limit."""
        while True:
            now = time.time()
            self._drop_old(now)
            waits = []
            if len(self.hourly_times) >= self.hourly_limit:
                waits.append(60 * 60 - (now - self.hourly_times[0]))
            if len(self.daily_times) >= self.daily_limit:
                waits.append(24 * 60 * 60 - (now - self.daily_times[0]))
            if not waits:
                return
            seconds = max(waits) + 1
            print(f"  rate limit reached, waiting {seconds:.0f} s ...")
            time.sleep(seconds)

    def record(self) -> None:
        now = time.time()
        self.hourly_times.append(now)
        self.daily_times.append(now)
        self.total += 1


# --------------------------------------------------------------------------- #
# Requests
# --------------------------------------------------------------------------- #

class BadRequest(Exception):
    """HTTP 400 - the request itself is wrong and must be fixed, not retried."""


def build_params(latitude: float, longitude: float, start: date, end: date) -> dict:
    return {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "auto",
    }


def fetch(session: requests.Session, params: dict, limiter: RateLimiter) -> dict:
    """Send one request with rate limiting and retries. Returns the parsed JSON."""
    for attempt in range(1, MAX_RETRIES + 1):
        limiter.wait()
        try:
            response = session.get(ENDPOINT, params=params, timeout=30)
        except requests.RequestException as exc:
            # network error / timeout: treat like a server error and retry
            limiter.record()
            retry_after = BACKOFF_BASE ** attempt
            print(f"  network error ({exc.__class__.__name__}), retry {attempt}/{MAX_RETRIES} in {retry_after}s")
            time.sleep(retry_after)
            continue
        limiter.record()

        status = response.status_code

        if status == 200:
            payload = response.json()
            if payload.get("error") is True or "daily" not in payload:
                raise RuntimeError(f"Unexpected response body: {payload}")
            return payload

        if status == 400:
            # The request is malformed. Retrying would not help.
            try:
                reason = response.json().get("reason", response.text)
            except ValueError:
                reason = response.text
            raise BadRequest(f"HTTP 400: {reason}")

        if status == 429 or status >= 500:
            retry_after = BACKOFF_BASE ** attempt
            print(f"  HTTP {status}, retry {attempt}/{MAX_RETRIES} in {retry_after}s")
            time.sleep(retry_after)
            continue

        # Any other status (e.g. 403, 404) is unexpected: fail loudly.
        response.raise_for_status()
        raise RuntimeError(f"Unexpected HTTP status {status}")

    raise RuntimeError(f"Gave up after {MAX_RETRIES} attempts")


# --------------------------------------------------------------------------- #
# Collection loop
# --------------------------------------------------------------------------- #

def year_ranges(start_year: int, end_date: date) -> list[tuple[int, date, date]]:
    """Split [start_year-01-01, end_date] into calendar years."""
    ranges = []
    for year in range(start_year, end_date.year + 1):
        start = date(year, 1, 1)
        end = min(date(year, 12, 31), end_date)
        ranges.append((year, start, end))
    return ranges


def collect() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    limiter = RateLimiter()
    ranges = year_ranges(START_YEAR, END_DATE)

    print(f"Collecting {len(LOCATIONS)} locations x {len(ranges)} years "
          f"({START_YEAR}-01-01 .. {END_DATE}) into {OUTPUT_DIR}/")

    saved = skipped = failed = 0
    t0 = time.time()

    with requests.Session() as session:
        for location, (latitude, longitude) in LOCATIONS.items():
            for year, start, end in ranges:
                output = OUTPUT_DIR / f"{location}_{year}.json"

                # Cache: never download a file that already exists.
                if output.exists():
                    skipped += 1
                    print(f"skip  {output.name} (already exists)")
                    continue

                params = build_params(latitude, longitude, start, end)
                try:
                    payload = fetch(session, params, limiter)
                except BadRequest as exc:
                    print(f"ERROR {output.name}: {exc}")
                    print("      Fix the request parameters before running again.")
                    sys.exit(1)
                except Exception as exc:  # noqa: BLE001 - report and continue
                    failed += 1
                    print(f"FAIL  {output.name}: {exc}")
                    continue

                # Store the response exactly as received (no processing).
                output.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                saved += 1
                n_days = len(payload["daily"]["time"])
                print(f"saved {output.name} ({n_days} days)")
                time.sleep(PAUSE_BETWEEN_REQUESTS)

    elapsed = time.time() - t0
    print()
    print(f"Done in {elapsed:.0f} s. saved={saved} skipped={skipped} failed={failed} "
          f"requests_sent={limiter.total}")
    if failed:
        print("Some files failed. Run the script again to retry only those.")


if __name__ == "__main__":
    collect()
