# Handoff: ML Project Part A (Group 58)

This file is for whoever continues the work (Tal + her Claude). Read it first.
The full assignment is in `ML_Project_Part_A_Instructions.docx` (Hebrew). A Hebrew guide
with the ML concepts and the full work plan is in `project_guide.html` (open it in a browser).

## Rules we are following

- Python only. The submission is a ZIP named `Group_58.zip`.
- Git: public repo https://github.com/talohayon14/ml_project_58 (branch `main`, pushed 2026-11-15). Commits use
  talohayon14@users.noreply.github.com. The course instructions docx is git-ignored (not ours to publish).
  `.gitattributes` keeps `data/` byte-for-byte (no line-ending conversion). The notebook merges badly: one person edits it at a time, pull first.
- `sensing.py` must never call the API. Only `data_collection.py` talks to Open-Meteo.
- Raw JSON files in `data/raw/` are stored exactly as received and never edited.
- No information from the next day may be used as a feature (RainTomorrow is built from it, that's all).
- The notebook is in plain English, no over-polished "AI" tone. The report (PDF) will be in Hebrew,
  max 10 pages, Arial 12, 1.5 spacing, cover page with group number + ID numbers only (no names).
- Tal must understand every line of code; the course deducts points otherwise.

## What is done

| Step | File | Status |
|---|---|---|
| 0. Environment | `.venv`, `requirements.txt`, `README.md` (first line `Group: 58`) | done |
| 1. Collection | `data_collection.py` -> 102 JSON files in `data/raw/` (6 cities x 2010..2026-11-07) | done, verified: all files complete, zero nulls |
| 2. Sensing | `sensing.py` -> `data/raw/sensed_data.csv` | done: 36,930 rows x 12 cols, 0 duplicates, 0 date gaps |
| 3. Target | `dataset_creation.ipynb` sections 1-2 -> `data/processed/final_dataset.csv` | done: 36,924 rows x 13 cols |
| 4. Problem definition (report text) | - | not started |
| 5. EDA | notebook section 3 (3.1-3.7) | done 2026-11-15: dictionary, KDE/bar plots, balance, Spearman heatmap, 4 relations (persistence, month x city, wind direction polar, temp range), target-related features, redundancy check. Helper columns live in `eda`, `df` is unchanged |
| 6. Data quality | notebook section 4 (4.1-4.5) | done 2026-11-15: no missing/duplicates; 10 sanity checks (1 mean<min row, 70 light-snow 0 mm rows, both rounding); extremes kept; model breaks found (wind jumps Jan 2017 and end of 2024) |
| 7. Data preparation | notebook section 5 (5.1-5.6) | done 2026-11-15: `make_features(days)` + `json_to_days(payload, location)` + `FEATURES_TO_DROP`; single-day features only, nothing fitted; final_dataset.csv = 36,924 x 34 (2 ids, 31 features, target). Wind speed dropped (unstable across models), feels_minus_actual dropped (MI ~0) |
| 8. Report (PDF) | - | not started |
| 9. Reproducibility check + ZIP | - | not started |

## Decisions already made (and why, for the report)

- Date range 2010-01-01 to 2026-11-07: many seasons/years, since the final test in part B is on future data.
  Stopped one week before today because the archive lags a few days.
- One request per city x year (102 requests), file name `<city>_<year>.json`. Small files, easy to re-download one.
- Only the 10 required daily variables, nothing extra.
- Rate limiter counts every request (including failed attempts). Retry with backoff 2,4,8,16,32 s on 429/5xx/network
  errors; stop with a message on 400. Existing files are skipped (cache).
- RainTomorrow is created in the notebook, not in `sensing.py`. The instructions are ambiguous about this;
  the appendix says the notebook includes "creating the target variable". Still worth asking the TA.
- Last day of each city (2026-11-07) is dropped because it has no "tomorrow".

## Findings so far

- No missing values anywhere, no duplicates, no date gaps. Expected, because Open-Meteo historical data is
  reanalysis (ERA5 model output), not raw station measurements. Say this in the data-quality section.
- Target prior: 36.2% rainy, 63.8% dry. Imbalanced ~1:2. Baseline "always 0" = 63.8% accuracy.
- Rainy-day share by city: vancouver 45.2%, tokyo 36.6%, london 35.9%, new_york 33.8%, berlin 33.6%, sydney 32.2%.
- Max `weather_code` in the data is 75: no shower codes (80-82) or thunderstorm codes (95-99) at daily resolution.
- `precipitation_sum` vs `rain_sum`: the difference is snow (e.g. berlin 2010-01-01: precip 3.2, rain 0.0, code 73).
- One day with 183.6 mm precipitation: new_york 2022-10-04 (code 65, 24 h). Next largest: tokyo 2019-10-12 (150.5, Typhoon Hagibis),
  tokyo 2026-06-03, sydney 2020-02-09, tokyo 2013-10-16. The New York one is suspicious, check it in section 4.
- EDA results: rain today -> 55.7% rain tomorrow vs 25.2% after a dry day. Wet wind direction differs per city
  (Vancouver: east 72%, west 22%). Vancouver wet in winter, Tokyo wet in summer. temp_range median 6.5 vs 7.9.
  Snow days (precip > rain) are exactly codes 71/73/75.
- The .venv was rebuilt on 2026-11-15 (Python 3.12.10 via winget). The project is in OneDrive, so a .venv made on another
  computer syncs over and breaks; rebuild it on each machine.

## Open questions for the TA

1. Should RainTomorrow be created in `sensing.py` or in the notebook?
2. In part B, how many days does each raw test JSON contain? One day, or a sequence?
   This decides whether lag features (yesterday's rain, 3-day rolling) are allowed.

## Ideas for the next steps (not done yet)

EDA (35 pts): variable dictionary with types; KDE plots for >= 3 continuous vars, bar plots for >= 2 categorical
(location, weather_code grouped); conditional distributions by RainTomorrow; Spearman correlation heatmap
(expect temperature vars ~0.9+, precipitation_sum ~ rain_sum); >= 3 "interesting" relations, e.g.
rain today -> rain tomorrow persistence, wind direction -> rain per city (polar plot), season x city
(Sydney is reversed), temp range (max-min) vs rain.

Quality: sanity checks (min > max, mean outside [min,max], negative precip, rain > precip, hours outside 0..24,
precip > 0 with 0 hours, rain weather code with 0 precip).

Preparation (30 pts): drop redundant vars with justification (e.g. keep one temperature + temp_range; keep
precipitation_sum, derive snow flag from precip - rain); group weather_code into ~7 categories; discretize
at least one continuous var with domain thresholds; new features: rain_today, temp_range, month sin/cos,
season by hemisphere, wind u/v components, one-hot location; lag features only if the TA says test samples
contain previous days. Write the feature code as one function that also works on a raw JSON sample (part B).

## How to run

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python data_collection.py      # skips files that already exist
python sensing.py
jupyter notebook dataset_creation.ipynb   # Kernel -> Restart & Run All
```

Do not copy `.venv` between computers; recreate it from `requirements.txt`.
