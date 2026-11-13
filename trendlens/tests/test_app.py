import io

import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DB_PATH": str(tmp_path / "t.db"),
                      "UPLOAD_DIR": str(tmp_path / "up"), "SEED_SAMPLES": True})
    return app.test_client()


def test_all_pages_load(client):
    for url in ["/", "/upload", "/history", "/regression", "/about"]:
        assert client.get(url).status_code == 200


def test_seeded_samples_show_in_history(client):
    html = client.get("/history").get_data(as_text=True)
    assert "City air quality" in html and "Quarterly sales" in html


def test_dashboard_renders_and_horizon_param_works(client):
    assert client.get("/dashboard/1").status_code == 200
    assert client.get("/dashboard/1?h=99").status_code == 200  # clamped, no crash


def test_unknown_run_is_404(client):
    assert client.get("/dashboard/9999").status_code == 404


def test_upload_valid_csv_then_analyze(client):
    csv = b"Year,Val\n2020,1\n2021,2\n2022,3\n2023,5\n2024,6\n2025,8\n"
    r = client.post("/upload", data={"file": (io.BytesIO(csv), "mine.csv")}, content_type="multipart/form-data")
    html = r.get_data(as_text=True)
    assert "Run analysis" in html
    token = html.split('name="token" value="')[1].split('"')[0]
    r = client.post("/analyze", data={"token": token, "filename": "mine.csv", "label_col": "Year", "value_col": "Val", "horizon": 3})
    assert r.status_code == 302 and "/dashboard/" in r.headers["Location"]


def test_upload_wrong_type_shows_error(client):
    r = client.post("/upload", data={"file": (io.BytesIO(b"hi"), "x.txt")}, content_type="multipart/form-data")
    assert "Only CSV" in r.get_data(as_text=True)


def test_upload_empty_csv_shows_error(client):
    r = client.post("/upload", data={"file": (io.BytesIO(b""), "x.csv")}, content_type="multipart/form-data")
    assert "empty" in r.get_data(as_text=True)


def test_no_file_chosen(client):
    r = client.post("/upload", data={}, content_type="multipart/form-data")
    assert "choose a CSV" in r.get_data(as_text=True)


def test_too_few_rows_flashes_error(client):
    csv = b"Year,Val\n2020,1\n2021,2\n"
    r = client.post("/upload", data={"file": (io.BytesIO(csv), "s.csv")}, content_type="multipart/form-data")
    token = r.get_data(as_text=True).split('name="token" value="')[1].split('"')[0]
    r = client.post("/analyze", data={"token": token, "label_col": "Year", "value_col": "Val"}, follow_redirects=True)
    assert "At least 5" in r.get_data(as_text=True)


def test_bad_token_rejected(client):
    r = client.post("/analyze", data={"token": "../../etc/passwd"}, follow_redirects=True)
    assert "Upload a file first" in r.get_data(as_text=True)


def test_sample_analysis_and_delete(client):
    r = client.post("/analyze", data={"sample": "fuel", "horizon": 5})
    assert r.status_code == 302
    assert client.post("/history/1/delete").status_code == 302
    assert client.get("/dashboard/1").status_code == 404


def test_compare_page_is_gone(client):
    assert client.get("/compare").status_code == 404


def test_regression_upload_runs_all_models(client):
    rows = ["size,hp,kind,price"] + [f"{100 + i % 40},{80 + i % 25},{'a' if i % 2 else 'b'},{4000 + 40 * (i % 40) + 20 * (i % 25) + (i % 7) * 30}" for i in range(120)]
    r = client.post("/regression", data={"file": (io.BytesIO("\n".join(rows).encode()), "cars.csv")},
                    content_type="multipart/form-data")
    html = r.get_data(as_text=True)
    assert r.status_code == 200 and "Best model" in html and "Lasso" in html