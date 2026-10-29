"""SQLite persistence for saved analyses."""
import json
import sqlite3
from contextlib import closing

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    unit TEXT, step TEXT, horizon INTEGER,
    labels TEXT NOT NULL, vals TEXT NOT NULL,
    r2 REAL, slope REAL, direction TEXT
)"""


def _conn(path):
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    return c


def init_db(path):
    with closing(_conn(path)) as c, c:
        c.execute(SCHEMA)


def save_run(path, name, labels, values, unit, step, horizon, r2, slope, direction):
    with closing(_conn(path)) as c, c:
        cur = c.execute(
            "INSERT INTO runs (name, unit, step, horizon, labels, vals, r2, slope, direction) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (name, unit, step, horizon, json.dumps(labels), json.dumps(values), r2, slope, direction),
        )
        return cur.lastrowid


def list_runs(path):
    with closing(_conn(path)) as c:
        return [dict(r) for r in c.execute(
            "SELECT id, name, created_at, unit, step, r2, slope, direction FROM runs ORDER BY id DESC")]


def get_run(path, run_id):
    with closing(_conn(path)) as c:
        row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    run = dict(row)
    run["labels"] = json.loads(run.pop("labels"))
    run["values"] = json.loads(run.pop("vals"))
    return run


def delete_run(path, run_id):
    with closing(_conn(path)) as c, c:
        return c.execute("DELETE FROM runs WHERE id = ?", (run_id,)).rowcount > 0
