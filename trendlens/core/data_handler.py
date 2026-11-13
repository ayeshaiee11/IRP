"""Data handling: load, validate, clean and describe CSV datasets."""
import re
from pathlib import Path

import pandas as pd

MIN_ROWS = 5


class DataError(ValueError):
    """Raised when a dataset cannot be used. The message is safe to show to users."""


def load_dataset(path):
    """Read a CSV file into a DataFrame, raising DataError with a friendly message on failure."""
    p = Path(path)
    if p.suffix.lower() != ".csv":
        raise DataError("Only CSV files are supported.")
    try:
        df = pd.read_csv(p)
    except pd.errors.EmptyDataError:
        raise DataError("The file is empty.")
    except Exception:
        raise DataError("Could not read the file. Make sure it is a valid CSV.")
    if df.empty or df.shape[1] < 2:
        raise DataError("The CSV needs at least two columns and some rows.")
    return df


def suggest_columns(df):
    """Guess the label column (first) and the value column (first numeric other than the label)."""
    label = df.columns[0]
    numeric = [c for c in df.select_dtypes("number").columns if c != label]
    if not numeric:
        raise DataError("No numeric column found. Add a column with numbers to predict.")
    return {"label": label, "value": numeric[0], "numeric": numeric}


def clean_data(df, label_col, value_col):
    """Return (labels, values) as clean lists. Drops rows with missing or non-numeric values."""
    for col in (label_col, value_col):
        if col not in df.columns:
            raise DataError(f"Column '{col}' was not found in the file.")
    if label_col == value_col:
        raise DataError("Choose different columns for labels and values.")
    sub = df[[label_col, value_col]].copy()
    sub[value_col] = pd.to_numeric(sub[value_col], errors="coerce")
    sub = sub.dropna(subset=[value_col]).drop_duplicates()
    if len(sub) < MIN_ROWS:
        raise DataError(f"At least {MIN_ROWS} rows with numbers are needed, found {len(sub)}.")
    labels = [str(x) if pd.notna(x) else str(i + 1) for i, x in enumerate(sub[label_col])]
    values = [float(v) for v in sub[value_col]]
    return labels, values


def guess_step(labels):
    """Describe the spacing of the labels in words (year, quarter, month or step)."""
    if all(re.fullmatch(r"Q\d+", str(x)) for x in labels):
        return "quarter"
    if all(re.fullmatch(r"\d{4}", str(x)) for x in labels):
        return "year"
    try:
        d = pd.to_datetime(pd.Series(labels))
        gap = (d.iloc[-1] - d.iloc[-2]).days
        return "month" if 27 <= gap <= 32 else "day"
    except Exception:
        return "step"


def extend_labels(labels, steps):
    """Create labels for the forecast periods that continue the pattern of the existing ones."""
    last = str(labels[-1]).strip()
    m = re.fullmatch(r"([A-Za-z]*)(\d+)", last)
    if m:
        prefix, num = m.groups()
        return [f"{prefix}{int(num) + k:0{len(num)}d}" for k in range(1, steps + 1)]
    try:
        d = pd.to_datetime(pd.Series(labels[-2:]))
        gap = (d.iloc[1] - d.iloc[0]).days
        end = d.iloc[1]
        if 27 <= gap <= 32:
            return [(end + pd.DateOffset(months=k)).strftime("%Y-%m-%d") for k in range(1, steps + 1)]
        return [(end + pd.Timedelta(days=gap * k)).strftime("%Y-%m-%d") for k in range(1, steps + 1)]
    except Exception:
        return [f"+{k}" for k in range(1, steps + 1)]
