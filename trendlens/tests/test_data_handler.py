import pandas as pd
import pytest

from core import data_handler as dh


def write(tmp_path, text, name="d.csv"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_load_valid_csv(tmp_path):
    df = dh.load_dataset(write(tmp_path, "Year,Value\n2020,1\n2021,2\n"))
    assert list(df.columns) == ["Year", "Value"]


def test_empty_file_gives_friendly_error(tmp_path):
    with pytest.raises(dh.DataError, match="empty"):
        dh.load_dataset(write(tmp_path, ""))


def test_wrong_extension(tmp_path):
    with pytest.raises(dh.DataError, match="CSV"):
        dh.load_dataset(write(tmp_path, "a,b\n1,2\n", "d.txt"))


def test_single_column_rejected(tmp_path):
    with pytest.raises(dh.DataError):
        dh.load_dataset(write(tmp_path, "a\n1\n2\n"))


def test_suggest_columns_picks_first_numeric(tmp_path):
    df = pd.DataFrame({"Year": ["2020", "2021"], "Name": ["a", "b"], "Val": [1, 2]})
    assert dh.suggest_columns(df)["value"] == "Val"


def test_no_numeric_column_error():
    with pytest.raises(dh.DataError, match="numeric"):
        dh.suggest_columns(pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]}))


def test_clean_data_drops_missing_and_text_values():
    df = pd.DataFrame({"Y": list("abcdefgh"), "V": [1, 2, None, 4, "oops", 6, 7, 8]})
    labels, values = dh.clean_data(df, "Y", "V")
    assert len(values) == 6 and None not in values


def test_clean_data_needs_five_rows():
    df = pd.DataFrame({"Y": list("abc"), "V": [1, 2, 3]})
    with pytest.raises(dh.DataError, match="At least 5"):
        dh.clean_data(df, "Y", "V")


def test_same_column_for_both_rejected():
    df = pd.DataFrame({"Y": range(6), "V": range(6)})
    with pytest.raises(dh.DataError):
        dh.clean_data(df, "V", "V")


def test_extend_labels_for_years_quarters_and_dates():
    assert dh.extend_labels(["2022", "2023"], 2) == ["2024", "2025"]
    assert dh.extend_labels(["Q3", "Q4"], 2) == ["Q5", "Q6"]
    assert dh.extend_labels(["2024-01-01", "2024-02-01"], 1) == ["2024-03-01"]


def test_guess_step():
    assert dh.guess_step(["Q1", "Q2"]) == "quarter"
    assert dh.guess_step(["2020", "2021"]) == "year"
