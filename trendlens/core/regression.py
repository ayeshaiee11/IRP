"""Multi-column regression: predict one target column from all the other columns.

Compares Linear, Ridge, Lasso, feature selection (SelectKBest), Polynomial (degree 2)
and feature extraction (PCA). Built to cope with large, messy CSV files.
"""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler

from .data_handler import DataError

MAX_ROWS = 50_000        # train on a sample of very large files, to stay fast
MAX_CATEGORIES = 50      # text columns with more distinct values are dropped (names, IDs...)
MIN_ROWS = 20
PREFER = ("price", "target", "salary", "cost", "sales", "revenue", "value", "y")


def numeric_columns(df):
    return [str(c) for c in df.select_dtypes("number").columns]


def default_target(df):
    """Pick the column to predict: a well-filled numeric column, preferring names like 'price'."""
    nums = numeric_columns(df)
    if not nums:
        raise DataError("No numeric column found to predict.")
    counts = {c: int(df[c].notna().sum()) for c in nums}
    usable = [c for c in nums if counts[c] >= MIN_ROWS] or nums
    for key in PREFER:
        for c in usable:
            if key in c.lower():
                return c
    return max(reversed(usable), key=lambda c: counts[c])  # fullest column, last one wins ties


def _alphas():
    return np.logspace(-2, 3, 20)


def _clean_name(n):
    return str(n).split("__", 1)[-1]


def _num(x, nd=3):
    x = float(x)
    return None if not np.isfinite(x) else round(x, nd)


def run_regression(df, target):
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    target = str(target)
    if target not in df.columns:
        raise DataError(f"Column '{target}' was not found in the file.")

    y = pd.to_numeric(df[target], errors="coerce")
    keep = y.notna()
    if keep.sum() < MIN_ROWS:
        raise DataError(f"The target column needs at least {MIN_ROWS} numeric rows, found {int(keep.sum())}.")
    X = df.loc[keep].drop(columns=[target])
    y = y[keep]
    total_rows = len(y)

    if total_rows > MAX_ROWS:
        idx = y.sample(MAX_ROWS, random_state=42).index
        X, y = X.loc[idx], y.loc[idx]

    # Drop columns that cannot help: all empty, constant, ID-like or too many distinct text values.
    dropped = []
    for c in list(X.columns):
        col = X[c]
        n_unique = col.nunique(dropna=True)
        is_num = pd.api.types.is_numeric_dtype(col)
        if n_unique <= 1 or (not is_num and n_unique > MAX_CATEGORIES) or (n_unique == len(col) and not pd.api.types.is_float_dtype(col)):
            dropped.append(c)
    X = X.drop(columns=dropped)
    if X.shape[1] == 0:
        raise DataError("No usable feature columns were left after cleaning.")

    num = list(X.select_dtypes("number").columns)
    cat = [c for c in X.columns if c not in num]
    parts = []
    if num:
        parts.append(("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num))
    if cat:
        parts.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                       ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat))
    prep = ColumnTransformer(parts, sparse_threshold=0)  # sparse_threshold=0 -> always a dense array

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    Xtr_t, Xte_t = prep.fit_transform(Xtr), prep.transform(Xte)
    names = [_clean_name(n) for n in prep.get_feature_names_out()]
    nf = Xtr_t.shape[1]

    k_sel = min(10, nf)
    k_poly = min(12, nf)
    models = {
        "Linear": (Pipeline([("m", LinearRegression())]),
                   "Plain linear regression (the baseline)."),
        "Ridge": (Pipeline([("m", RidgeCV(alphas=_alphas()))]),
                  "Linear + L2 penalty. Shrinks coefficients; good when columns are correlated."),
        "Lasso": (Pipeline([("m", LassoCV(cv=5, max_iter=5000, random_state=0))]),
                  "Linear + L1 penalty. Sets weak features to exactly zero (built-in feature selection)."),
        "Feature selection": (Pipeline([("sel", SelectKBest(f_regression, k=k_sel)), ("m", LinearRegression())]),
                              f"SelectKBest keeps the {k_sel} strongest features, then linear regression."),
        "Polynomial (deg 2)": (Pipeline([("sel", SelectKBest(f_regression, k=k_poly)),
                                         ("poly", PolynomialFeatures(2, include_bias=False)),
                                         ("sc", StandardScaler()),
                                         ("m", RidgeCV(alphas=_alphas()))]),
                               f"Top {k_poly} features, plus squares and pair products, then Ridge. Captures curves."),
        "PCA + Ridge": (Pipeline([("pca", PCA(0.95)), ("m", RidgeCV(alphas=_alphas()))]),
                        "Feature extraction: PCA builds new combined features keeping 95% of the variation."),
    }

    results, fitted = [], {}
    for name, (pipe, desc) in models.items():
        row = {"name": name, "desc": desc, "test_r2": None, "train_r2": None, "rmse": None, "note": "", "error": None}
        try:
            pipe.fit(Xtr_t, ytr)
            pred_te, pred_tr = pipe.predict(Xte_t), pipe.predict(Xtr_t)
            row["test_r2"] = _num(r2_score(yte, pred_te))
            row["train_r2"] = _num(r2_score(ytr, pred_tr))
            row["rmse"] = _num(np.sqrt(mean_squared_error(yte, pred_te)), 2)
            m = pipe.named_steps["m"]
            if name == "Ridge":
                row["note"] = f"alpha = {m.alpha_:.3g}"
            elif name == "Lasso":
                kept = [names[i] for i in np.flatnonzero(m.coef_)]
                row["note"] = f"kept {len(kept)} of {nf} features: " + ", ".join(kept[:6]) + ("..." if len(kept) > 6 else "")
            elif name == "Feature selection":
                mask = pipe.named_steps["sel"].get_support()
                row["note"] = "kept: " + ", ".join(n for n, k in zip(names, mask) if k)
            elif name == "PCA + Ridge":
                row["note"] = f"{pipe.named_steps['pca'].n_components_} components from {nf} features"
            if row["train_r2"] is not None and row["test_r2"] is not None and row["train_r2"] - row["test_r2"] > 0.15:
                row["note"] = ("Possible overfitting (train score much higher than test). " + row["note"]).strip()
            fitted[name] = pipe
        except Exception as e:  # one failing model must not break the whole page
            row["error"] = f"Could not fit: {type(e).__name__}"
        results.append(row)

    ok = [r for r in results if r["test_r2"] is not None]
    if not ok:
        raise DataError("None of the models could be fitted on this data.")
    best = max(ok, key=lambda r: r["test_r2"])

    # Actual vs predicted for the best model (max 800 points, so the chart stays light).
    pred = fitted[best["name"]].predict(Xte_t)
    rng = np.random.default_rng(0)
    pick = rng.choice(len(yte), size=min(800, len(yte)), replace=False)
    points = [{"x": _num(yte.iloc[i], 2), "y": _num(pred[i], 2)} for i in pick]
    lo, hi = float(min(yte.min(), pred.min())), float(max(yte.max(), pred.max()))

    # Biggest drivers: standardized Ridge coefficients (comparable across features).
    drivers = []
    if "Ridge" in fitted:
        coef = fitted["Ridge"].named_steps["m"].coef_
        order = np.argsort(-np.abs(coef))[:8]
        drivers = [{"name": names[i], "coef": _num(coef[i], 3)} for i in order]

    return {
        "target": target, "rows_total": int(total_rows), "rows_used": int(len(y)),
        "n_features": nf, "dropped": dropped, "models": results, "best": best["name"],
        "best_r2": best["test_r2"], "points": points, "line": [_num(lo, 2), _num(hi, 2)],
        "drivers": drivers,
        "target_stats": {"min": _num(y.min(), 2), "max": _num(y.max(), 2), "mean": _num(y.mean(), 2)},
    }