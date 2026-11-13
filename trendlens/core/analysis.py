"""Turns raw labels/values into a result dict the dashboard can render."""
import re
import numpy as np
from . import model as M
from .llm import suggest_factors

MAX_HORIZON = 12


def _next_labels(labels, horizon):
    last = str(labels[-1])
    m = re.match(r"^(.*?)(\d+)$", last)
    if m:
        prefix, num = m.group(1), m.group(2)
        return [f"{prefix}{int(num) + i}".zfill(0) for i in range(1, horizon + 1)]
    return [f"+{i}" for i in range(1, horizon + 1)]


def _fmt(v):
    return f"{v:,.2f}".rstrip("0").rstrip(".")


FACTORS = [
    (("fuel", "petrol", "diesel", "oil", "gas"),
     ["crude oil prices", "taxes and duties", "the rupee/dollar exchange rate", "refinery and supply costs"]),
    (("sale", "revenue", "income", "profit"),
     ["demand and seasonality", "pricing changes", "marketing or new products", "competition"]),
    (("air", "aqi", "pm2", "pm10", "pollution", "emission"),
     ["traffic and industry", "weather and season", "crop burning", "pollution rules"]),
    (("temp", "rain", "climate"),
     ["season and climate patterns", "long-term climate change", "measurement changes"]),
    (("price", "cost", "inflation"),
     ["inflation", "supply and demand", "input costs", "taxes"]),
    (("population", "user", "customer", "visitor", "student"),
     ["growth in demand", "migration or access changes", "marketing and awareness"]),
]


def _factors(title, unit):
    text = f"{title} {unit}".lower()
    for keys, items in FACTORS:
        if any(k in text for k in keys):
            return items
    return []


def _reasons(labels, values, direction, bp_label, rmse, fitted):
    y = np.asarray(values, dtype=float)
    n = len(y)
    out = []
    first, last = y[0], y[-1]
    change = last - first
    if abs(first) > 1e-12:
        out.append(f"From {labels[0]} to {labels[-1]} the value moved from {_fmt(first)} to {_fmt(last)} "
                   f"({change / abs(first) * 100:+.1f}%).")
    diffs = np.diff(y)
    if direction != "Flat" and len(diffs):
        up = direction == "Rising"
        agree = int(np.sum(diffs > 0) if up else np.sum(diffs < 0))
        out.append(f"It {'rose' if up else 'fell'} in {agree} of {len(diffs)} periods, "
                   f"so the {'rise' if up else 'fall'} is {'steady' if agree / len(diffs) >= 0.75 else 'bumpy'}.")
    if len(diffs):
        i, j = int(np.argmax(diffs)), int(np.argmin(diffs))
        if diffs[i] > 0:
            out.append(f"The biggest jump was at {labels[i + 1]} ({diffs[i]:+,.2f}).")
        if diffs[j] < 0:
            out.append(f"The biggest drop was at {labels[j + 1]} ({diffs[j]:+,.2f}).")
    h = n // 2
    s1 = np.polyfit(np.arange(h + 1), y[:h + 1], 1)[0]
    s2 = np.polyfit(np.arange(n - h), y[h:], 1)[0]
    if s1 * s2 < 0:
        out.append("The direction reversed between the first and second half of the data.")
    elif abs(s1) > 1e-12 and abs(s2) / abs(s1) > 1.3:
        out.append("The change is speeding up in the second half.")
    elif abs(s1) > 1e-12 and abs(s2) / abs(s1) < 0.7:
        out.append("The change is slowing down in the second half.")
    if bp_label:
        out.append(f"The trend changes pace around {bp_label}, which is worth investigating.")
    if rmse > 1e-12:
        odd = [str(labels[k]) for k in range(n) if abs(y[k] - fitted[k]) > 2 * rmse]
        if odd:
            out.append(f"Unusual points far from the trendline: {', '.join(odd[:3])}.")
    return out


def analyze(title, labels, values, horizon=5, unit="", step="period", **_ignored):
    period = str(step) if step else "period"
    horizon = max(1, min(int(horizon), MAX_HORIZON))
    values = [float(v) for v in values]
    model, metrics = M.fit_model(values)
    trend = M.get_trendline(model, len(values))
    fc = M.forecast(model, values, horizon)
    for f, lab in zip(fc, _next_labels(labels, horizon)):
        f["label"] = lab
    bp = M.detect_breakpoints(values)

    slope = trend["slope"]
    span = (max(values) - min(values)) or 1.0
    if abs(slope) < 0.01 * span / len(values):
        direction, verb = "Flat", "staying roughly flat"
    elif slope > 0:
        direction, verb = "Rising", "increasing"
    else:
        direction, verb = "Falling", "decreasing"

    u = f" {unit}" if unit else ""
    summary = (f"{title} is {verb} by about {_fmt(abs(slope))}{u} per {period}. "
               f"The line explains {metrics['r2'] * 100:.0f}% of the variation (R² = {metrics['r2']:.2f}). "
               f"By {fc[-1]['label']} it is forecast to reach about {_fmt(fc[-1]['value'])}{u} "
               f"(range {_fmt(fc[-1]['lower'])} to {_fmt(fc[-1]['upper'])}).")
    breakpoint_label = None
    if bp is not None:
        breakpoint_label = str(labels[bp])
        summary += f" The trend appears to change around {breakpoint_label}."

    reasons = _reasons(labels, values, direction, breakpoint_label, metrics["rmse"], trend["fitted"])
    pct = (values[-1] - values[0]) / abs(values[0]) * 100 if abs(values[0]) > 1e-12 else None
    factors = suggest_factors(title, unit, labels[0], labels[-1], direction, pct)
    factors_source = "AI" if factors else "keywords"
    if not factors:
        factors = _factors(title, unit)
    if reasons:
        summary += " What the data shows: " + " ".join(reasons[:4])
    if factors:
        summary += (f" Possible real-world factors to check ({'AI-suggested, ' if factors_source == 'AI' else ''}not proven by this data): "
                    + ", ".join(factors) + ".")

    metrics["n"] = metrics["rows"] = len(values)
    return {
        "step": period, "n": len(values), "rows": len(values),
        "reasons": reasons, "factors": factors, "factors_source": factors_source,
        "title": title, "labels": [str(l) for l in labels], "values": values,
        "unit": unit, "period": period, "horizon": horizon,
        "trend": trend, "slope": slope, "intercept": trend["intercept"],
        "metrics": metrics, "r2": metrics["r2"], "forecast": fc,
        "direction": direction, "breakpoint": bp, "breakpoint_label": breakpoint_label,
        "summary": summary,
    }