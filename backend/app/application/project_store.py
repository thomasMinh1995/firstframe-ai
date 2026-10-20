import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ProjectNotFound(Exception):
    pass


class ProjectConflict(Exception):
    pass


class ProjectStore:
    """Local project storage with optimistic locking to protect concurrent edits."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS projects "
                    "(id TEXT PRIMARY KEY, revision INTEGER NOT NULL, data TEXT NOT NULL)"
                )
                yield connection
        finally:
            connection.close()

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT data FROM projects").fetchall()
        return sorted(
            (json.loads(row[0]) for row in rows), key=lambda item: item["updated_at"], reverse=True
        )

    def get(self, project_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT data FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
        if row is None:
            raise ProjectNotFound
        return json.loads(row[0])

    def create(self, project: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO projects (id, revision, data) VALUES (?, ?, ?)",
                (project["id"], project["revision"], json.dumps(project, ensure_ascii=False)),
            )
        return project

    def save(self, project: dict[str, Any], expected_revision: int) -> dict[str, Any]:
        saved = {
            **project,
            "revision": expected_revision + 1,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE projects SET revision = ?, data = ? WHERE id = ? AND revision = ?",
                (
                    saved["revision"],
                    json.dumps(saved, ensure_ascii=False),
                    saved["id"],
                    expected_revision,
                ),
            )
            if cursor.rowcount != 1:
                raise ProjectConflict
        return saved
