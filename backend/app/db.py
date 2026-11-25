"""SQLite storage.

Decision for v0.1: SQLite instead of PostgreSQL keeps the demo to a single
container. All SQL lives in this module, so switching to PostgreSQL later
touches nothing else (NFR-21).
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    client TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT,
    commit_sha TEXT,
    grade TEXT,
    overall REAL,
    scores TEXT,
    tools TEXT,
    stats TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS findings (
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    tool TEXT, rule_id TEXT, characteristic TEXT, severity TEXT,
    file TEXT, line INTEGER, message TEXT, snippet TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_analysis ON findings(analysis_id);
CREATE INDEX IF NOT EXISTS idx_analyses_client_created ON analyses(client, created_at);
"""

_UPDATABLE = ("status", "stage", "commit_sha", "grade", "overall", "scores", "tools", "stats", "error",
              "finished_at")
_UPDATE_SQL = (
    "UPDATE analyses SET status = COALESCE(?, status), stage = COALESCE(?, stage), "
    "commit_sha = COALESCE(?, commit_sha), "
    "grade = COALESCE(?, grade), overall = COALESCE(?, overall), scores = COALESCE(?, scores), "
    "tools = COALESCE(?, tools), stats = COALESCE(?, stats), error = COALESCE(?, error), "
    "finished_at = COALESCE(?, finished_at) WHERE id = ?"
)

_SEVERITY_ORDER = "CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(analyses)")}
            if "stage" not in columns:  # databases created by v0.1
                conn.execute("ALTER TABLE analyses ADD COLUMN stage TEXT")

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with self._lock, conn:
                yield conn
        finally:
            conn.close()

    # --- analyses -------------------------------------------------------
    def create_analysis(self, repo_url: str, client: str) -> str:
        analysis_id = str(uuid.uuid4())  # random IDs, not sequential (R7)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO analyses (id, repo_url, client, status, created_at) VALUES (?, ?, ?, 'queued', ?)",
                (analysis_id, repo_url, client, now_iso()),
            )
        return analysis_id

    def update_analysis(self, analysis_id: str, **fields) -> None:
        """Update selected columns. Review fix (S608): one static statement, no SQL built from strings;
        columns that are not passed keep their value through COALESCE."""
        unknown = set(fields) - set(_UPDATABLE)
        if unknown:
            raise ValueError(f"Unknown fields: {unknown}")
        values = [json.dumps(fields[k]) if k in {"scores", "tools", "stats"} and k in fields else fields.get(k)
                  for k in _UPDATABLE]
        with self._connect() as conn:
            conn.execute(_UPDATE_SQL, (*values, analysis_id))

    def get_analysis(self, analysis_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return _row_to_analysis(row) if row else None

    def list_analyses(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [_row_to_analysis(r) for r in rows]

    def history_for_repo(self, repo_url: str, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM analyses WHERE repo_url = ? AND status IN ('completed', 'partial') "
                "ORDER BY created_at DESC LIMIT ?", (repo_url, limit)).fetchall()
        return [_row_to_analysis(r) for r in rows]

    def delete_analysis(self, analysis_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        return cursor.rowcount > 0

    def mark_cancelled(self, analysis_id: str) -> bool:
        """FR-14: stop a queued or running analysis. False if it has already finished."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE analyses SET status = 'cancelled', error = 'Cancelled by the user.', finished_at = ? "
                "WHERE id = ? AND status IN ('queued', 'running')", (now_iso(), analysis_id))
        return cursor.rowcount > 0

    def count_active(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM analyses WHERE status IN ('queued', 'running')").fetchone()[0]

    def count_recent_for_client(self, client: str, since_iso: str) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM analyses WHERE client = ? AND created_at >= ?",
                                (client, since_iso)).fetchone()[0]

    def fail_interrupted(self) -> int:
        """NFR-15: on start-up, jobs left 'running' by a crash are marked failed."""
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE analyses SET status = 'failed', error = 'Interrupted by a server restart.', "
                "finished_at = ? WHERE status IN ('queued', 'running')", (now_iso(),))
        return cursor.rowcount

    # --- findings -------------------------------------------------------
    def add_findings(self, analysis_id: str, findings: list[dict]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO findings (analysis_id, tool, rule_id, characteristic, severity, file, line, message, "
                "snippet) VALUES (:analysis_id, :tool, :rule_id, :characteristic, :severity, :file, :line, "
                ":message, :snippet)",
                [f | {"analysis_id": analysis_id} for f in findings],
            )

    def list_findings(self, analysis_id: str, characteristic: str | None = None, severity: str | None = None,
                      file: str | None = None, limit: int = 500) -> list[dict]:
        query = "SELECT tool, rule_id, characteristic, severity, file, line, message, snippet FROM findings " \
                "WHERE analysis_id = ?"
        params: list = [analysis_id]
        if characteristic:
            query += " AND characteristic = ?"
            params.append(characteristic)
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        if file:
            query += " AND file LIKE ?"
            params.append(f"%{file}%")
        query += f" ORDER BY {_SEVERITY_ORDER}, file, line LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]


def _row_to_analysis(row: sqlite3.Row) -> dict:
    data = dict(row)
    data.pop("client", None)  # never exposed through the API
    for key in ("scores", "tools", "stats"):
        data[key] = json.loads(data[key]) if data[key] else None
    return data
