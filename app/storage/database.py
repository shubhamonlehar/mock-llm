from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS llm_fixtures (
    id INTEGER PRIMARY KEY,
    request_hash TEXT UNIQUE NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    created_at TEXT NOT NULL,
    request_json TEXT NOT NULL,
    response_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_llm_fixtures_request_hash
    ON llm_fixtures(request_hash);

CREATE INDEX IF NOT EXISTS idx_llm_fixtures_model
    ON llm_fixtures(model);

CREATE INDEX IF NOT EXISTS idx_llm_fixtures_created_at
    ON llm_fixtures(created_at);
"""


def connect(sqlite_path: Path | str) -> sqlite3.Connection:
    path = Path(sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(sqlite_path: Path | str) -> None:
    with connect(sqlite_path) as connection:
        connection.executescript(SCHEMA)
