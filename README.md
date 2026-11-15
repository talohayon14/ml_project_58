Group: 58

# פרויקט למידת מכונה, חלק א': חיזוי RainTomorrow

סיווג בינארי של `RainTomorrow`: האם ביום הבא ירדו לפחות 1.0 מ"מ משקעים,
על בסיס נתוני מזג אוויר יומיים משש ערים (London, New York, Sydney, Berlin, Tokyo, Vancouver)
שנאספו מ-Open-Meteo Historical Weather API.

## מבנה הפרויקט

```
ml_project/
├── data/
│   ├── raw/                  # קובצי JSON גולמיים מה-API, בדיוק כפי שהתקבלו + sensed_data.csv
│   └── processed/            # final_dataset.csv (אחרי עיבוד, כולל RainTomorrow)
├── data_collection.py        # איסוף הנתונים מה-API: ניהול קצב בקשות, טיפול בשגיאות, שמירת JSON
├── sensing.py                # קריאת ה-JSON המקומי, איחוד לטבלה אחת, הוספת location ו-date, הסרת כפילויות
├── dataset_creation.ipynb    # ניתוח הנתונים, בדיקות איכות, הכנת הנתונים ויצירת משתנה המטרה
├── requirements.txt          # החבילות והגרסאות הדרושות
└── README.md
```

## התקנה

דרוש Python 3.12.

```
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

## סדר הרצה

1. `python data_collection.py` - מוריד את הנתונים הגולמיים ל-`data/raw/`.
   קבצים שכבר קיימים לא יורדים שוב.
2. `python sensing.py` - מאחד את קובצי ה-JSON ל-`data/raw/sensed_data.csv`.
   קובץ זה אינו פונה ל-API.
3. `jupyter notebook dataset_creation.ipynb` - ניתוח, עיבוד ויצירת `data/processed/final_dataset.csv`.
