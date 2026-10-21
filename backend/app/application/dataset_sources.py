"""Read local exports and imported recordings without creating storage or invoking AI."""

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from pathlib import Path
from typing import Any

from app.application.dataset import get_dataset_store


def dataset_directories() -> list[Path]:
    directory = get_dataset_store().directory
    configured = os.getenv("DEMO_DATASET_DIR", "").strip()
    return (
        [Path(configured).expanduser().resolve()]
        if configured
        else [directory, Path(__file__).resolve().parents[3] / "demo" / "datasets"]
    )


def exported_values() -> Iterator[dict[str, Any]]:
    database = get_dataset_store().directory / "reviews.sqlite3"
    active = {}
    if database.exists():
        with closing(sqlite3.connect(database, timeout=10)) as connection:
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='dataset_active_branches'"
            ).fetchone():
                for run_id, data in connection.execute(
                    "SELECT a.run_id, b.data FROM dataset_active_branches a JOIN dataset_branches b "
                    "ON a.run_id=b.run_id AND a.branch_id=b.branch_id"
                ):
                    active[run_id] = json.loads(data)["recording"]
    for directory in dataset_directories():
        for path in sorted(
            {
                *directory.glob("*.json"),
                *directory.glob("*.jsonl"),
                *(directory / "runs").glob("*.json"),
            }
        ):
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            for text in content.splitlines() if path.suffix == ".jsonl" else [content]:
                try:
                    value = json.loads(text)
                except ValueError:
                    continue
                if isinstance(value, dict) and value.get("run_id") not in active:
                    yield value
    if database.exists():
        with closing(sqlite3.connect(database, timeout=10)) as connection:
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='imported_samples'"
            ).fetchone():
                for (data,) in connection.execute(
                    "SELECT data FROM imported_samples ORDER BY run_id"
                ):
                    value = json.loads(data)
                    if value["run_id"] not in active:
                        yield value
    yield from active.values()
