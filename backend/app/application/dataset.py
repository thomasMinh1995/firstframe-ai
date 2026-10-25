"""Local workflow recordings; SQLite is the durable source for exported samples."""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from app.application.ai_provider import (
    ProviderMetadata,
    StructuredProvider,
    StructuredRequest,
    StructuredResult,
    strict_json_instructions,
)
from app.application.progress import report_progress
from app.application.project_store import ProjectConflict

logger = logging.getLogger(__name__)
_active_run: ContextVar["DatasetRun | None"] = ContextVar("dataset_run", default=None)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class DatasetStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.database = directory / "dataset.sqlite3"

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.directory.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database, timeout=10)
        try:
            with connection:
                connection.execute(
                    "CREATE TABLE IF NOT EXISTS dataset_runs ("
                    "id TEXT PRIMARY KEY, project_id TEXT, analysis_id TEXT, "
                    "status TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL)"
                )
                yield connection
        finally:
            connection.close()

    def save(self, record: dict[str, Any]) -> None:
        snapshot = record["output"] or record["input"]
        analysis = snapshot.get("analysis") or {}
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO dataset_runs VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET analysis_id=excluded.analysis_id, "
                "status=excluded.status, data=excluded.data",
                (
                    record["run_id"],
                    record["project_id"],
                    analysis.get("artifact_id"),
                    record["status"],
                    record["started_at"],
                    _json(record),
                ),
            )

    def parent_run(self, project_id: str | None, analysis_id: str | None) -> str | None:
        if not project_id or not analysis_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM dataset_runs WHERE project_id=? AND analysis_id=? "
                "AND status='completed' ORDER BY created_at DESC, id DESC LIMIT 1",
                (project_id, analysis_id),
            ).fetchone()
        return str(row[0]) if row else None

    def records(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT data FROM dataset_runs ORDER BY created_at, id"
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def export_run(self, record: dict[str, Any]) -> None:
        _atomic_write(self.directory / "runs" / f"{record['run_id']}.json", _json(record) + "\n")

    def export(self, jsonl_path: Path | None = None) -> int:
        if jsonl_path is not None and jsonl_path.resolve() == self.database.resolve():
            raise ValueError("The JSONL destination must not overwrite the dataset database.")
        records = self.records()
        for record in records:
            if record["status"] != "running":
                self.export_run(record)
        if jsonl_path is not None:
            _atomic_write(jsonl_path, "".join(_json(record) + "\n" for record in records))
        return len(records)


def get_dataset_store() -> DatasetStore:
    load_dotenv()
    default = Path(__file__).resolve().parents[2] / ".data" / "datasets"
    configured = os.getenv("DATASET_DIR", "").strip()
    return DatasetStore(Path(configured).expanduser().resolve() if configured else default)


class DatasetRun:
    def __init__(self, store: DatasetStore, operation: str, snapshot: dict[str, Any]) -> None:
        self.store = store
        snapshot = json.loads(_json(snapshot))
        analysis_id = (snapshot.get("analysis") or {}).get("artifact_id")
        parent = None
        try:
            parent = store.parent_run(snapshot.get("id"), analysis_id)
        except (OSError, sqlite3.Error) as error:
            self._warn(error)
        self.record: dict[str, Any] = {
            "schema_version": 1,
            "run_id": str(uuid4()),
            "operation": operation,
            "project_id": snapshot.get("id"),
            "parent_run_id": parent,
            "source_analysis_id": analysis_id,
            "input_revision": snapshot.get("revision"),
            "output_revision": None,
            "started_at": _now(),
            "finished_at": None,
            "status": "running",
            "workflow_complete": False,
            "review_status": "unreviewed",
            "human_feedback": None,
            "input": snapshot,
            "output": None,
            "steps": [],
            "models_used": [],
            "error_type": None,
        }
        self.persist()

    def _warn(self, error: Exception) -> None:
        logger.warning(
            "Dataset write failed; workflow continues. exception_class=%s", type(error).__name__
        )

    def persist(self) -> None:
        try:
            self.store.save(self.record)
        except (OSError, sqlite3.Error) as error:
            self._warn(error)

    def complete(self, snapshot: dict[str, Any], *, workflow_complete: bool | None = None) -> None:
        self.record["output"] = json.loads(_json(snapshot))
        self.record["output_revision"] = snapshot.get("revision")
        self.record["workflow_complete"] = (self.record["operation"] in {"plan", "generate"}
                                            if workflow_complete is None else workflow_complete)
        self._finish("completed")

    def _finish(self, status: str) -> None:
        self.record["status"] = status
        self.record["finished_at"] = _now()
        self.record["models_used"] = [
            {"provider": provider, "model": model}
            for provider, model in dict.fromkeys(
                (step["provider"], step["model"])
                for step in self.record["steps"]
                if step["model"] is not None
            )
        ]
        self.persist()
        try:
            self.store.export_run(self.record)
        except OSError as error:
            self._warn(error)


class RecordingProvider:
    def __init__(self, provider: StructuredProvider, run: DatasetRun) -> None:
        self.provider = provider
        self.run = run

    @property
    def metadata(self) -> ProviderMetadata:
        return self.provider.metadata

    def request_structured(self, request: StructuredRequest) -> StructuredResult:
        metadata = self.metadata
        schema = request.response_model.model_json_schema()
        effective_instructions = strict_json_instructions(request)
        step: dict[str, Any] = {
            "stage": request.stage,
            "provider": metadata.provider,
            "requested_model": metadata.model,
            "model": None,
            "parameters": metadata.parameters,
            "started_at": _now(),
            "duration_ms": None,
            "status": "running",
            "request": {
                "instructions": request.instructions,
                "effective_instructions": effective_instructions,
                "input_text": request.input_text,
                "response_schema": schema,
                "prompt_sha256": _hash(effective_instructions),
                "schema_sha256": _hash(_json(schema)),
                "input_sha256": _hash(request.input_text),
            },
            "output": None,
            "raw_output": None,
            "response_id": None,
            "error_type": None,
        }
        self.run.record["steps"].append(step)
        self.run.persist()
        started = time.monotonic()
        report_progress(request.stage, "active")
        try:
            result = self.provider.request_structured(request)
        except Exception as error:
            report_progress(request.stage, "failed")
            step.update(
                status="failed",
                error_type=type(error).__name__,
                raw_output=getattr(error, "raw_output", None),
            )
            raise
        else:
            report_progress(request.stage, "completed")
            step.update(
                status="completed",
                model=result.model,
                output=result.output.model_dump(mode="json"),
                raw_output=result.raw_output,
                response_id=result.response_id,
            )
            return result
        finally:
            step["duration_ms"] = round((time.monotonic() - started) * 1000)
            self.run.persist()


def recording_provider(provider: StructuredProvider) -> StructuredProvider:
    run = _active_run.get()
    return RecordingProvider(provider, run) if run is not None else provider


@contextmanager
def capture_workflow(operation: str, snapshot: dict[str, Any]) -> Iterator[DatasetRun]:
    run = DatasetRun(get_dataset_store(), operation, snapshot)
    token = _active_run.set(run)
    try:
        yield run
    except Exception as error:
        run.record["error_type"] = type(error).__name__
        run._finish("conflict" if isinstance(error, ProjectConflict) else "failed")
        raise
    finally:
        _active_run.reset(token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-export local workflow datasets from SQLite.")
    parser.add_argument("--output", type=Path, help="Also write all records to a JSONL file.")
    args = parser.parse_args()
    store = get_dataset_store()
    count = store.export(args.output)
    print(f"Exported {count} workflow records from {store.database}")


if __name__ == "__main__":
    main()
