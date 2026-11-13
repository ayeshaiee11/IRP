"""Linear trend model, forecast with 95% interval, and breakpoint detection (numpy only)."""
import numpy as np

MIN_ROWS = 5


def _clean(values):
    y = np.asarray(values, dtype=float)
    if y.ndim != 1 or len(y) < MIN_ROWS:
        raise ValueError(f"At least {MIN_ROWS} data rows are needed.")
    if not np.all(np.isfinite(y)):
        raise ValueError("Values must be numbers with no blanks or NaN.")
    return y


def fit_model(values):
    """Fit y = slope*x + intercept. Returns (model, metrics)."""
    y = _clean(values)
    n = len(y)
    x = np.arange(n, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    resid = y - pred
    sse = float(np.sum(resid ** 2))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 if sst < 1e-12 else 1.0 - sse / sst
    model = {
        "slope": float(slope), "intercept": float(intercept), "n": n,
        "x_mean": float(x.mean()), "sxx": float(np.sum((x - x.mean()) ** 2)),
        "resid_std": float(np.sqrt(sse / (n - 2))),
    }
    metrics = {
        "r2": float(r2),
        "mae": float(np.mean(np.abs(resid))),
        "rmse": float(np.sqrt(np.mean(resid ** 2))),
    }
    return model, metrics


def get_trendline(model, n):
    x = np.arange(n, dtype=float)
    fitted = (model["slope"] * x + model["intercept"]).tolist()
    return {
        "slope": model["slope"], "intercept": model["intercept"],
        "fitted": fitted, "values": fitted,
    }


def forecast(model, values, horizon):
    """Next `horizon` points with a 95% prediction interval that widens with distance."""
    n = model["n"]
    out = []
    for i in range(horizon):
        x0 = n + i
        value = model["slope"] * x0 + model["intercept"]
        se = model["resid_std"] * np.sqrt(1 + 1 / n + (x0 - model["x_mean"]) ** 2 / model["sxx"])
        margin = 1.96 * se
        out.append({"value": float(value), "lower": float(value - margin), "upper": float(value + margin)})
    return out


def detect_breakpoints(values):
    """Index where the trend changes slope, or None if one straight line fits well."""
    y = _clean(values)
    n = len(y)
    x = np.arange(n, dtype=float)

    def sse(cols):
        A = np.column_stack(cols)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        return float(np.sum((y - A @ coef) ** 2))

    ones = np.ones(n)
    sse_lin = sse([ones, x])
    sst = float(np.sum((y - y.mean()) ** 2))
    if sst < 1e-12 or sse_lin < 1e-9 * max(1.0, sst):
        return None
    best_k, best = None, sse_lin
    for k in range(2, n - 2):
        s = sse([ones, x, np.maximum(0.0, x - k)])
        if s < best:
            best_k, best = k, s
    if best_k is not None and best < 0.5 * sse_lin:
        return int(best_k)
    return None