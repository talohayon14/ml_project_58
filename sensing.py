"""Sensing: turn the raw Open-Meteo JSON files into one table.

Reads every JSON file in data/raw/, converts the "daily" block of each
file into rows (one row per day), adds the columns `location` and `date`,
concatenates everything, removes duplicate (location, date) rows and
writes data/raw/sensed_data.csv.

This script never contacts the API. It only reads local files.

Run:  python sensing.py
"""

import json
from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")
OUTPUT_FILE = RAW_DIR / "sensed_data.csv"

# The daily variables we expect in every file (same list as data_collection.py).
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


def location_from_filename(path: Path) -> str:
    """'data/raw/new_york_2015.json' -> 'new_york'.

    The API response does not contain the city name, only coordinates,
    so the name is taken from the file name written by data_collection.py.
    """
    stem = path.stem                      # 'new_york_2015'
    location, _year = stem.rsplit("_", 1)  # split on the LAST underscore
    return location


def load_one_file(path: Path) -> pd.DataFrame:
    """Read one raw JSON file and return a DataFrame with one row per day."""
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)

    if "daily" not in payload:
        raise ValueError(f"{path.name}: no 'daily' block in file")

    daily = payload["daily"]
    missing = [v for v in DAILY_VARIABLES if v not in daily]
    if missing:
        raise ValueError(f"{path.name}: missing variables {missing}")

    # daily = {"time": [...], "weather_code": [...], ...}  -> columns
    df = pd.DataFrame(daily)
    df = df.rename(columns={"time": "date"})
    df["location"] = location_from_filename(path)
    return df


def sense(raw_dir: Path = RAW_DIR, output_file: Path = OUTPUT_FILE) -> pd.DataFrame:
    files = sorted(raw_dir.glob("*.json"))
    if not files:
        raise FileNotFoundError(f"No JSON files found in {raw_dir}/ - run data_collection.py first")

    print(f"Reading {len(files)} files from {raw_dir}/")
    frames = [load_one_file(path) for path in files]
    df = pd.concat(frames, ignore_index=True)
    rows_before = len(df)

    # Remove duplicate days (same location + same date).
    df = df.drop_duplicates(subset=["location", "date"], keep="first")
    duplicates_removed = rows_before - len(df)

    # Tidy up: parse dates, sort, put the identifying columns first.
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["location", "date"]).reset_index(drop=True)
    df = df[["location", "date"] + DAILY_VARIABLES]

    df.to_csv(output_file, index=False)

    print(f"Rows read:            {rows_before}")
    print(f"Duplicates removed:   {duplicates_removed}")
    print(f"Rows written:         {len(df)}")
    print(f"Columns:              {len(df.columns)}")
    print(f"Date range:           {df['date'].min().date()} .. {df['date'].max().date()}")
    print("Rows per location:")
    print(df["location"].value_counts().sort_index().to_string())
    print(f"\nSaved {output_file}")
    return df


if __name__ == "__main__":
    sense()
