"""Flask application: routes that connect the website to the model, data handling and storage."""
import math
import os
import re
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from core import data_handler as dh
from core import regression as rg
from core import storage
from core.analysis import analyze

BASE = Path(__file__).parent
SAMPLES = {
    "air": ("City air quality", "sample_air_quality.csv"),
    "fuel": ("Fuel prices", "sample_fuel_prices.csv"),
    "sales": ("Quarterly sales", "sample_sales.csv"),
}
TOKEN_RE = re.compile(r"^[a-f0-9]{32}\.csv$")

# ---------- Bitcoin Price & ROI Predictor ----------
BTC_CSV = BASE / "data" / "btc.csv"
BTC_HORIZONS = (7, 14, 30, 90)
BTC_SENTIMENT = {"bullish": 1.25, "neutral": 1.0, "bearish": 0.75}
BTC_FIT_DAYS = None  # None = fit on every row; e.g. 365 = fit only on the most recent year
BTC_DEFAULTS = {"amount": 1000.0, "horizon": 30, "sentiment": "neutral"}


def btc_load():
    """Load historical Bitcoin prices from data/btc.csv."""
    if not BTC_CSV.exists():
        raise FileNotFoundError("data/btc.csv was not found.")

    raw = pd.read_csv(BTC_CSV)

    cols = {str(c).strip().lower(): c for c in raw.columns}

    if "time" not in cols or "priceusd" not in cols:
        raise ValueError("btc.csv needs 'time' and 'PriceUSD' columns.")

    df = pd.DataFrame({
        "Date": pd.to_datetime(raw[cols["time"]], errors="coerce"),
        "Close": pd.to_numeric(raw[cols["priceusd"]], errors="coerce")
    })

    df = df.dropna()
    df = df[df["Close"] > 0]
    df = df.sort_values("Date")
    df = df.drop_duplicates("Date", keep="last").reset_index(drop=True)

    if len(df) < 10:
        raise ValueError("Not enough valid Bitcoin price records.")

    return df


def btc_forecast(df, amount, horizon, sentiment):
    """Linear regression on Close, then a sentiment-adjusted forecast and portfolio ROI."""
    fit = df
    if BTC_FIT_DAYS:
        recent = df[df["Date"] >= df["Date"].iloc[-1] - pd.Timedelta(days=BTC_FIT_DAYS)]
        if len(recent) >= 10:
            fit = recent
    t0 = fit["Date"].iloc[0]
    day = lambda s: (s - t0).dt.total_seconds().to_numpy(dtype=float) / 86400.0
    x, y = day(fit["Date"]), fit["Close"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - float(np.sum((y - (slope * x + intercept)) ** 2)) / ss_tot if ss_tot else 0.0

    # Sentiment scales the slope. On a downtrend the multiplier is mirrored, so
    # "bullish" always means a better outcome than "bearish".
    base = BTC_SENTIMENT[sentiment]
    mult = base if slope >= 0 else 2 - base
    eff = float(slope) * mult

    last_close = float(df["Close"].iloc[-1])
    last_date = df["Date"].iloc[-1]
    fc = [max(last_close + eff * d, 0.0) for d in range(1, horizon + 1)]
    fc_labels = [(last_date + pd.Timedelta(days=d)).strftime("%Y-%m-%d") for d in range(1, horizon + 1)]
    predicted = fc[-1]
    btc_owned = amount / last_close
    value = btc_owned * predicted
    profit = value - amount

    # Chart data: thin out the history for speed (the regression above used every row)
    n = len(df)
    idx = np.unique(np.linspace(0, n - 1, min(n, 600)).astype(int))
    all_x = day(df["Date"])
    hist = [round(float(v), 2) for v in df["Close"].to_numpy(dtype=float)[idx]]
    trend = [round(float(v), 2) for v in (slope * all_x + intercept)[idx]]
    hn = len(hist)
    chart = {
        "labels": df["Date"].dt.strftime("%Y-%m-%d").to_numpy()[idx].tolist() + fc_labels,
        "history": hist + [None] * horizon,
        "trend": trend + [None] * horizon,
        "forecast": [None] * (hn - 1) + [round(last_close, 2)] + [round(p, 2) for p in fc],
    }
    return {
        "chart": chart, "last_close": last_close, "last_date": last_date.strftime("%Y-%m-%d"),
        "predicted": predicted, "value": value, "profit": profit,
        "roi_pct": profit / amount * 100, "btc_owned": btc_owned,
        "slope": float(slope), "mult": mult, "r2": r2, "rows": n,
    }


def btc_context(args):
    """Template variables for the predictor. Inputs come from the query string (GET form)."""
    form = dict(BTC_DEFAULTS)
    try:
        amount = float(args.get("amount", form["amount"]))
        if math.isfinite(amount):
            form["amount"] = min(max(amount, 1.0), 1e9)
    except (TypeError, ValueError):
        pass
    horizon = args.get("horizon", type=int)
    if horizon in BTC_HORIZONS:
        form["horizon"] = horizon
    sentiment = (args.get("sentiment") or "").lower()
    if sentiment in BTC_SENTIMENT:
        form["sentiment"] = sentiment
    btc, error = None, None
    try:
        btc = btc_forecast(btc_load(), **form)
    except Exception as e:  # shown on the page instead of a 500 error
        error = str(e)
    return {"btc": btc, "btc_error": error, "btc_form": form, "btc_horizons": BTC_HORIZONS}


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        MAX_CONTENT_LENGTH=200 * 1024 * 1024,
        DB_PATH=str(BASE / "instance" / "trendlens.db"),
        UPLOAD_DIR=str(BASE / "uploads"),
        SEED_SAMPLES=True,
    )
    if config:
        app.config.update(config)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DB_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    storage.init_db(app.config["DB_PATH"])

    def db():
        return app.config["DB_PATH"]

    def analyze_and_save(name, df, label_col, value_col, horizon):
        labels, values = dh.clean_data(df, label_col, value_col)
        step = dh.guess_step(labels)
        result = analyze(name, labels, values, horizon, unit=str(value_col), step=step)
        return storage.save_run(
            db(), name, labels, values, str(value_col), step, result["horizon"],
            result["metrics"]["r2"], result["trend"]["slope"], result["direction"],
        )

    if app.config["SEED_SAMPLES"] and not storage.list_runs(db()):
        for name, fname in reversed(list(SAMPLES.values())):
            df = dh.load_dataset(BASE / "data" / fname)
            cols = dh.suggest_columns(df)
            analyze_and_save(name, df, cols["label"], cols["value"], 4)

    @app.context_processor
    def inject_btc():
        """Give regression.html the Bitcoin predictor variables (only on that page)."""
        if request.endpoint == "regression":
            return btc_context(request.args)
        return {}

    # ---------- pages ----------
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "GET":
            return render_template("upload.html", samples=SAMPLES)
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Please choose a CSV file first.", "error")
            return render_template("upload.html", samples=SAMPLES)
        if not file.filename.lower().endswith(".csv"):
            flash("Only CSV files are supported.", "error")
            return render_template("upload.html", samples=SAMPLES)
        token = uuid.uuid4().hex + ".csv"
        path = Path(app.config["UPLOAD_DIR"]) / token
        file.save(path)
        try:
            df = dh.load_dataset(path)
            cols = dh.suggest_columns(df)
        except dh.DataError as e:
            path.unlink(missing_ok=True)
            flash(str(e), "error")
            return render_template("upload.html", samples=SAMPLES)
        preview = df.head(5).fillna("").astype(str).to_dict("records")
        return render_template(
            "upload.html", samples=SAMPLES, step2=True, token=token, filename=file.filename,
            columns=[str(c) for c in df.columns], preview=preview, suggestion=cols,
        )

    @app.post("/analyze")
    def run_analysis():
        horizon = request.form.get("horizon", 4, type=int)
        try:
            sample = request.form.get("sample")
            if sample:
                if sample not in SAMPLES:
                    raise dh.DataError("Unknown sample dataset.")
                name, fname = SAMPLES[sample]
                df = dh.load_dataset(BASE / "data" / fname)
                cols = dh.suggest_columns(df)
                label_col, value_col = cols["label"], cols["value"]
            else:
                token = request.form.get("token", "")
                if not TOKEN_RE.match(token):
                    raise dh.DataError("Upload a file first.")
                path = Path(app.config["UPLOAD_DIR"]) / token
                if not path.exists():
                    raise dh.DataError("That upload has expired. Please upload the file again.")
                df = dh.load_dataset(path)
                label_col = request.form.get("label_col", "")
                value_col = request.form.get("value_col", "")
                name = (request.form.get("run_name") or Path(request.form.get("filename", "Upload")).stem)[:60]
            run_id = analyze_and_save(name, df, label_col, value_col, horizon)
        except (dh.DataError, ValueError) as e:
            flash(str(e), "error")
            return redirect(url_for("upload"))
        return redirect(url_for("dashboard", run_id=run_id))

    @app.route("/dashboard/<int:run_id>")
    def dashboard(run_id):
        run = storage.get_run(db(), run_id)
        if run is None:
            abort(404)
        horizon = request.args.get("h", run["horizon"], type=int)
        result = analyze(run["name"], run["labels"], run["values"], horizon, run["unit"], run["step"])
        chart = {
            "values": result["values"], "labels": result["labels"],
            "forecast": result["forecast"], "slope": result["trend"]["slope"],
            "intercept": result["trend"]["intercept"], "fitted": result["trend"]["fitted"],
        }
        return render_template("dashboard.html", run=run, r=result, chart=chart)

    @app.route("/history")
    def history():
        return render_template("history.html", runs=storage.list_runs(db()))

    @app.post("/history/<int:run_id>/delete")
    def delete(run_id):
        if storage.delete_run(db(), run_id):
            flash("Analysis deleted.", "ok")
        return redirect(url_for("history"))

    @app.route("/regression", methods=["GET", "POST"])
    def regression():
        if request.method == "GET":
            return render_template("regression.html")
        path, new_file = None, False
        try:
            token = request.form.get("token", "")
            if token:  # re-run on a file uploaded earlier, with another target column
                if not TOKEN_RE.match(token):
                    raise dh.DataError("Upload a file first.")
                path = Path(app.config["UPLOAD_DIR"]) / token
                if not path.exists():
                    raise dh.DataError("That upload has expired. Please upload the file again.")
                filename = request.form.get("filename", "your file")
            else:
                file = request.files.get("file")
                if not file or not file.filename:
                    raise dh.DataError("Please choose a CSV file first.")
                if not file.filename.lower().endswith(".csv"):
                    raise dh.DataError("Only CSV files are supported.")
                token, new_file, filename = uuid.uuid4().hex + ".csv", True, file.filename
                path = Path(app.config["UPLOAD_DIR"]) / token
                file.save(path)
            df = dh.load_dataset(path)
            target = request.form.get("target") or rg.default_target(df)
            result = rg.run_regression(df, target)
        except (dh.DataError, ValueError) as e:
            if new_file and path is not None:
                path.unlink(missing_ok=True)
            flash(str(e), "error")
            return render_template("regression.html")
        return render_template("regression.html", r=result, token=token, filename=filename,
                               columns=rg.numeric_columns(df))

    @app.route("/about")
    def about():
        return render_template("about.html")

    # ---------- errors ----------
    @app.errorhandler(404)
    def not_found(_):
        return render_template("error.html", code=404, message="That page or analysis does not exist."), 404

    @app.errorhandler(413)
    def too_large(_):
        return render_template("error.html", code=413, message="The file is too large. The limit is 200 MB."), 413

    @app.errorhandler(500)
    def server_error(_):
        return render_template("error.html", code=500, message="Something went wrong on our side."), 500

    return app


if __name__ == "__main__":
    create_app().run(debug=True)