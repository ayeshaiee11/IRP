import numpy as np
import pytest

from core import model as M
from core.analysis import analyze


def test_perfect_line_has_exact_slope_and_r2():
    model, metrics = M.fit_model([10, 12, 14, 16, 18, 20])
    trend = M.get_trendline(model, 6)
    assert trend["slope"] == pytest.approx(2.0)
    assert trend["intercept"] == pytest.approx(10.0)
    assert metrics["r2"] == pytest.approx(1.0)
    assert metrics["mae"] == pytest.approx(0.0, abs=1e-9)


def test_forecast_continues_the_line_and_interval_contains_value():
    values = [10, 12, 14, 16, 18, 20]
    model, _ = M.fit_model(values)
    fc = M.forecast(model, values, 3)
    assert [round(f["value"]) for f in fc] == [22, 24, 26]
    assert all(f["lower"] <= f["value"] <= f["upper"] for f in fc)


def test_interval_widens_with_distance():
    values = [10, 13, 11, 15, 14, 18, 17]
    model, _ = M.fit_model(values)
    fc = M.forecast(model, values, 4)
    widths = [f["upper"] - f["lower"] for f in fc]
    assert widths == sorted(widths)


def test_too_few_rows_raises():
    with pytest.raises(ValueError):
        M.fit_model([1, 2, 3])


def test_nan_values_raise():
    with pytest.raises(ValueError):
        M.fit_model([1, 2, float("nan"), 4, 5, 6])


def test_constant_data_does_not_crash():
    model, metrics = M.fit_model([5, 5, 5, 5, 5, 5])
    assert M.get_trendline(model, 6)["slope"] == pytest.approx(0.0, abs=1e-9)
    assert M.detect_breakpoints([5, 5, 5, 5, 5, 5]) is None


def test_breakpoint_found_when_trend_changes():
    flat_then_steep = [10, 10.2, 10.1, 10.3, 10.2, 14, 18, 22, 26, 30]
    assert M.detect_breakpoints(flat_then_steep) in (4, 5, 6)


def test_no_breakpoint_on_straight_line():
    assert M.detect_breakpoints(list(np.arange(10) * 2.0 + 1)) is None


def test_analyze_returns_summary_and_labels():
    r = analyze("Test", ["2020", "2021", "2022", "2023", "2024", "2025"], [1, 2, 3, 4, 5, 6], 2, "units", "year")
    assert r["direction"] == "Rising"
    assert [f["label"] for f in r["forecast"]] == ["2026", "2027"]
    assert "increasing" in r["summary"]


def test_horizon_is_clamped():
    r = analyze("T", list("abcdef"), [1, 2, 3, 4, 5, 6], 99)
    assert r["horizon"] == 12
