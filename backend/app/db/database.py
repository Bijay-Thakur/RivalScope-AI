"""SQLite persistence for RivalScope.

Zero external dependencies (stdlib ``sqlite3``) so the app has real, durable
persistence out of the box — no server, no credentials. The Provider Settings
screen advertises "SQLite -> Postgres"; this is the SQLite tier. A new
connection is opened per operation (SQLite connections are not thread-safe and
FastAPI runs DB work in a threadpool via ``asyncio.to_thread``).
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# DB path is overridable via env (tests point this at a temp file so they never
# pollute the dev run-history DB).
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(os.environ.get("RIVALSCOPE_DB_PATH", _DEFAULT_DATA_DIR / "rivalscope.db"))
DATA_DIR = DB_PATH.parent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_runs (
    run_id              TEXT PRIMARY KEY,
    our_company         TEXT NOT NULL,
    competitor          TEXT NOT NULL,
    market              TEXT NOT NULL,
    report_type         TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'completed',
    research_mode       TEXT,
    confidence_score    REAL,
    source_count        INTEGER DEFAULT 0,
    evidence_count      INTEGER DEFAULT 0,
    verified_claim_count INTEGER DEFAULT 0,
    warning_count       INTEGER DEFAULT 0,
    duration_ms         REAL,
    created_at          TEXT NOT NULL,
    report_json         TEXT
);

CREATE TABLE IF NOT EXISTS run_traces (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL,
    seq         INTEGER NOT NULL,
    ts          TEXT,
    kind        TEXT NOT NULL,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL,
    summary     TEXT,
    track       TEXT,
    duration_ms REAL,
    detail_json TEXT,
    FOREIGN KEY (run_id) REFERENCES research_runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_run_traces_run_id ON run_traces(run_id);

CREATE TABLE IF NOT EXISTS evaluations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_name         TEXT NOT NULL,
    created_at              TEXT NOT NULL,
    model_provider          TEXT,
    research_mode           TEXT,
    eval_mode               TEXT,
    judge_model             TEXT,
    total_tasks             INTEGER,
    average_score           REAL,
    average_latency_seconds REAL,
    average_source_count    REAL,
    result_json             TEXT
);
"""


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
