from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any

from app.storage.database import connect, init_db


@dataclass(frozen=True)
class Fixture:
    request_hash: str
    provider: str
    model: str | None
    created_at: str
    request: dict[str, Any]
    response: dict[str, Any]


class FixtureRepository:
    def __init__(self, sqlite_path: Path | str) -> None:
        self.sqlite_path = Path(sqlite_path)
        init_db(self.sqlite_path)
        self._lock = RLock()

    def upsert(
        self,
        *,
        request_hash: str,
        provider: str,
        model: str | None,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> Fixture:
        created_at = datetime.now(UTC).isoformat()
        request_json = json.dumps(request, sort_keys=True)
        response_json = json.dumps(response, sort_keys=True)
        with self._lock, connect(self.sqlite_path) as connection:
            connection.execute(
                """
                INSERT INTO llm_fixtures
                    (request_hash, provider, model, created_at, request_json, response_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_hash) DO UPDATE SET
                    provider = excluded.provider,
                    model = excluded.model,
                    created_at = excluded.created_at,
                    request_json = excluded.request_json,
                    response_json = excluded.response_json
                """,
                (request_hash, provider, model, created_at, request_json, response_json),
            )
        return Fixture(request_hash, provider, model, created_at, request, response)

    def get(self, request_hash: str) -> Fixture | None:
        with connect(self.sqlite_path) as connection:
            row = connection.execute(
                """
                SELECT request_hash, provider, model, created_at, request_json, response_json
                FROM llm_fixtures
                WHERE request_hash = ?
                """,
                (request_hash,),
            ).fetchone()
        return self._row_to_fixture(row) if row else None

    def count(self) -> int:
        with connect(self.sqlite_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM llm_fixtures").fetchone()
        return int(row["count"])

    def clear(self) -> int:
        with self._lock, connect(self.sqlite_path) as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM llm_fixtures").fetchone()
            deleted_count = int(row["count"])
            connection.execute("DELETE FROM llm_fixtures")
        return deleted_count

    def list_hashes(self) -> set[str]:
        with connect(self.sqlite_path) as connection:
            rows = connection.execute("SELECT request_hash FROM llm_fixtures").fetchall()
        return {str(row["request_hash"]) for row in rows}

    def search(
        self,
        *,
        model: str | None = None,
        date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Fixture]:
        clauses: list[str] = []
        params: list[Any] = []
        if model:
            clauses.append("model = ?")
            params.append(model)
        if date:
            clauses.append("created_at LIKE ?")
            params.append(f"{date}%")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.extend([limit, offset])

        with connect(self.sqlite_path) as connection:
            rows = connection.execute(
                f"""
                SELECT request_hash, provider, model, created_at, request_json, response_json
                FROM llm_fixtures
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                params,
            ).fetchall()
        return [self._row_to_fixture(row) for row in rows]

    def all(self) -> list[Fixture]:
        with connect(self.sqlite_path) as connection:
            rows = connection.execute(
                """
                SELECT request_hash, provider, model, created_at, request_json, response_json
                FROM llm_fixtures
                ORDER BY id ASC
                """
            ).fetchall()
        return [self._row_to_fixture(row) for row in rows]

    @staticmethod
    def _row_to_fixture(row: sqlite3.Row) -> Fixture:
        return Fixture(
            request_hash=str(row["request_hash"]),
            provider=str(row["provider"]),
            model=row["model"],
            created_at=str(row["created_at"]),
            request=json.loads(row["request_json"]),
            response=json.loads(row["response_json"]),
        )
