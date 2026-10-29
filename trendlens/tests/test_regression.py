import numpy as np
import pandas as pd
import pytest

from core import data_handler as dh
from core import regression as rg


def make_df(n=400):
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"id": range(n), "size": rng.normal(100, 20, n), "hp": rng.normal(90, 15, n),
                       "kind": rng.choice(["a", "b"], n)})
    df["price"] = 30 * df["size"] + 10 * df["hp"] + rng.normal(0, 100, n)
    return df


def test_default_target_prefers_price():
    assert rg.default_target(make_df()) == "price"


def test_all_models_run_and_id_column_dropped():
    r = rg.run_regression(make_df(), "price")
    assert len(r["models"]) == 6 and r["best_r2"] > 0.9
    assert "id" in r["dropped"] and all(m["error"] is None for m in r["models"])


def test_missing_values_and_text_are_handled():
    df = make_df()
    df.loc[::10, "hp"] = np.nan
    assert rg.run_regression(df, "price")["best_r2"] > 0.9


def test_bad_target_and_tiny_data():
    with pytest.raises(dh.DataError):
        rg.run_regression(make_df(), "nope")
    with pytest.raises(dh.DataError):
        rg.run_regression(make_df(10), "price")