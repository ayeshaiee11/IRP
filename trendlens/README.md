# TrendLens: Linear Regression Trendline for Prediction Data

A Flask website that takes a numeric dataset (CSV), fits a linear regression trendline, detects pattern changes,
forecasts future values with a 95% uncertainty range, and explains the result in plain English.

Project 311, MJ-IRP Python Programming Module (2026-27).

## Run it

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py                  # open http://127.0.0.1:5000
python -m pytest               # run all tests
```

## Folder guide (what each part does)

```
trendlens/
├── app.py                 Flask app. Routes (pages) that connect the website to the model, data handling and database.
├── requirements.txt       Libraries to install.
├── core/                  All the Python logic, separate from the website (clean architecture).
│   ├── data_handler.py    Load CSV, validate, clean (drop bad rows), suggest columns, build forecast labels.
│   ├── model.py           Linear regression (scikit-learn): fit, trendline, metrics, forecast, breakpoint detection.
│   ├── insights.py        Turns numbers into plain-English sentences.
│   ├── analysis.py        Runs the whole pipeline in one function: analyze().
│   └── storage.py         SQLite database: save, list, get and delete analyses.
├── templates/             HTML pages (Jinja). base.html is the shared layout; every page extends it.
├── static/
│   ├── css/style.css      All styling (dark theme, 3D cards, responsive hamburger menu).
│   └── js/
│       ├── main.js        Theme toggle, menu, card tilt, count-up numbers, animated bars.
│       └── chart3d.js     3D chart (Three.js).
├── data/                  Three sample datasets (air quality, fuel prices, sales).
├── uploads/               User-uploaded CSVs are saved here with random names.
├── instance/              The SQLite database file (trendlens.db) is created here.
└── tests/                 pytest tests: model, data handling, and the website.
```

## How a request flows

1. **Upload page** (`/upload`): user uploads a CSV (or picks a sample). `data_handler.load_dataset` checks it.
2. **Preview**: the first rows are shown, with suggested label and value columns.
3. **Analyze** (`/analyze`): `clean_data` removes bad rows, then `analysis.analyze` runs `model.fit_model`,
   `get_trendline`, `forecast`, `detect_breakpoints` and `insights.plain_english_summary`.
4. **Save**: `storage.save_run` stores the data and key results in SQLite.
5. **Dashboard** (`/dashboard/<id>`): shows stat cards, the 3D chart, the insights and a forecast table.
6. **History / Compare**: list, delete and compare saved analyses.

## The maths in one minute

- Time steps are numbered t = 0, 1, 2, ... and the model fits `y = intercept + slope * t`.
- **R²**: share of variation explained (1 is perfect). **MAE** and **RMSE**: average error size.
- **Forecast range**: 95% prediction interval, `value ± 1.96 * sigma * sqrt(1 + 1/n + (t - mean_t)² / Sxx)`. It widens further into the future.
- **Pattern change**: try every split point, fit two lines, and pick the best. If two lines cut the error by more than half versus one line, report it.

## Rubric coverage

| Week | Criteria | Where |
|---|---|---|
| 2 | Core features, processing logic, functions and code reuse | `core/model.py`, `core/analysis.py`, `base.html` layout reused by every page |
| 3 | Data handling, persistence, exception handling | `core/data_handler.py`, `core/storage.py`, `DataError` + error pages |
| 4 | Input validation, reports/visualisation, testing | upload validation, dashboard + 3D chart, `tests/` (33 tests) |

## Team split (rotation)

| | Week 2 | Week 3 | Week 4 |
|---|---|---|---|
| Ayesha | Model | Website | Data and testing |
| Mariyam | Website | Data and storage | Model |
| Nabiha | Data and cleaning | Model | Website |
