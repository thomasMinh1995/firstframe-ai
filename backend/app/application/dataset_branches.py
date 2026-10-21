"""Preserve both sides of import conflicts as immutable, portable branch snapshots."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.dataset_corrections import validate_corrections
from app.application.dataset_history import json_diff
from app.application.dataset_review import (
    ExportedSample,
    OutputVersion,
    Review,
    ReviewConflict,
    ReviewStore,
    fingerprint,
)
from app.application.dataset_sources import exported_values


class BranchReview(Review):
    model_config = ConfigDict(extra="forbid")


class BranchVersion(OutputVersion):
    model_config = ConfigDict(extra="forbid")


class SampleState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    recording: dict[str, Any]
    review: BranchReview
    history: list[BranchVersion] = Field(min_length=1)


class SavedBranch(SampleState):
    branch_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: Literal["local", "incoming", "restore"]
    created_at: str


class ConflictChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: Literal["local", "incoming"]
    local_token: str = Field(pattern=r"^[a-f0-9]{64}$")


def state_value(state: SampleState) -> dict[str, Any]:
    return state.model_dump(include={"fingerprint", "recording", "review", "history"})


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def validate_state(state: SampleState) -> None:
    sample = state.recording
    ExportedSample.model_validate(sample, strict=True)
    if state.fingerprint != fingerprint(sample):
        raise ValueError("Fingerprint bản gốc không khớp.")
    if (
        validate_corrections(sample, state.review.corrected_outputs)
        != state.review.corrected_outputs
    ):
        raise ValueError("Bản sửa hiện tại không hợp lệ.")
    for index, version in enumerate(state.history):
        if version.version != index:
            raise ValueError("Lịch sử phải liên tục từ bản gốc 0.")
        if validate_corrections(sample, version.corrected_outputs) != version.corrected_outputs:
            raise ValueError("Output trong lịch sử không hợp lệ.")
        if index == 0:
            if (
                version.action != "original"
                or version.corrected_outputs
                or version.restored_from is not None
            ):
                raise ValueError("Phiên bản 0 phải giữ nguyên bản gốc.")
        elif version.action == "restore":
            source = version.restored_from
            if (
                source is None
                or not 0 <= source < index
                or version.corrected_outputs != state.history[source].corrected_outputs
            ):
                raise ValueError("Tham chiếu khôi phục trong lịch sử không hợp lệ.")
        elif version.action not in {"edit", "imported"} or version.restored_from is not None:
            raise ValueError("Loại phiên bản lịch sử không hợp lệ.")
        elif version.action == "imported" and (index != 1 or not version.corrected_outputs):
            raise ValueError("Mốc sửa trước lịch sử không hợp lệ.")
    if state.history[-1].corrected_outputs != state.review.corrected_outputs:
        raise ValueError("Bản sửa hiện tại không khớp phiên bản cuối của lịch sử.")


def local_states(run_id: str, connection: sqlite3.Connection | None = None) -> list[SampleState]:
    records = {
        fingerprint(record): record
        for record in exported_values()
        if record.get("run_id") == run_id
    }
    store = ReviewStore()
    if connection is None and store.path.exists():
        with closing(sqlite3.connect(store.path, timeout=10)) as reader, reader:
            reader.execute("BEGIN")
            return _states(records, reader)
    return _states(records, connection)


def _states(records, connection):
    result = []
    has_reviews = (
        connection is not None
        and connection.execute("SELECT 1 FROM sqlite_master WHERE name='reviews'").fetchone()
    )
    for fp, record in sorted(records.items()):
        row = (
            connection.execute(
                "SELECT data FROM reviews WHERE run_id=? AND fingerprint=?", (record["run_id"], fp)
            ).fetchone()
            if has_reviews
            else None
        )
        review = Review.model_validate_json(row[0]) if row else Review()
        versions = (
            ReviewStore._versions(connection, record["run_id"], fp, review)
            if connection is not None
            else [OutputVersion(version=0, created_at=None, action="original")]
        )
        result.append(
            SampleState(
                recording=record,
                fingerprint=fp,
                review=BranchReview.model_validate(review.model_dump()),
                history=[
                    BranchVersion.model_validate(version.model_dump()) for version in versions
                ],
            )
        )
    return result


def local_token(states: list[SampleState]) -> str:
    return digest([state_value(state) for state in states])


def create_branch_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS dataset_branches (run_id TEXT, branch_id TEXT, data TEXT NOT NULL, PRIMARY KEY(run_id, branch_id))"
    )
    connection.execute(
        "CREATE TABLE IF NOT EXISTS dataset_active_branches (run_id TEXT PRIMARY KEY, branch_id TEXT NOT NULL)"
    )


def save_branch(connection: sqlite3.Connection, state: SampleState, source: str) -> SavedBranch:
    validate_state(state)
    value = state_value(state)
    branch = SavedBranch.model_validate(
        {
            **value,
            "branch_id": digest(value),
            "source": source,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    connection.execute(
        "INSERT OR IGNORE INTO dataset_branches VALUES (?, ?, ?)",
        (state.recording["run_id"], branch.branch_id, branch.model_dump_json()),
    )
    return branch


def saved_branches(run_id: str, connection: sqlite3.Connection | None = None) -> list[SavedBranch]:
    store = ReviewStore()
    if connection is None:
        if not store.path.exists():
            return []
        with closing(sqlite3.connect(store.path, timeout=10)) as reader:
            return saved_branches(run_id, reader)
    if not connection.execute(
        "SELECT 1 FROM sqlite_master WHERE name='dataset_branches'"
    ).fetchone():
        return []
    return [
        SavedBranch.model_validate_json(row[0])
        for row in connection.execute(
            "SELECT data FROM dataset_branches WHERE run_id=? ORDER BY branch_id", (run_id,)
        )
    ]


def write_active(
    connection: sqlite3.Connection,
    state: SampleState,
    current: list[SampleState],
    *,
    restore: bool = False,
) -> None:
    for old in current:
        save_branch(connection, old, "local")
    selected = save_branch(connection, state, "restore" if restore else "incoming")
    stored_revisions = [
        Review.model_validate_json(row[0]).revision
        for row in connection.execute(
            "SELECT data FROM reviews WHERE run_id=?", (state.recording["run_id"],)
        )
    ]
    review = state.review.model_copy(
        update={
            "revision": max(
                [
                    state.review.revision,
                    *stored_revisions,
                    *(old.review.revision for old in current),
                ]
            )
            + 1,
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    versions = list(state.history)
    if restore:
        review = review.model_copy(
            update={"status": "unreviewed", "use_for_demo": False, "use_for_training": False}
        )
        versions.append(
            BranchVersion(
                version=len(versions),
                created_at=review.updated_at,
                action="restore",
                restored_from=versions[-1].version,
                corrected_outputs=review.corrected_outputs,
            )
        )
    # Both complete paths are archived above before replacing the active path.
    connection.execute(
        "DELETE FROM output_versions WHERE run_id=? AND fingerprint=?",
        (state.recording["run_id"], state.fingerprint),
    )
    for version in versions[1:]:
        connection.execute(
            "INSERT INTO output_versions VALUES (?, ?, ?, ?)",
            (
                state.recording["run_id"],
                state.fingerprint,
                version.version,
                version.model_dump_json(),
            ),
        )
    connection.execute(
        "INSERT INTO reviews VALUES (?, ?, ?) ON CONFLICT(run_id, fingerprint) DO UPDATE SET data=excluded.data",
        (state.recording["run_id"], state.fingerprint, review.model_dump_json()),
    )
    connection.execute(
        "INSERT INTO dataset_active_branches VALUES (?, ?) ON CONFLICT(run_id) DO UPDATE SET branch_id=excluded.branch_id",
        (state.recording["run_id"], selected.branch_id),
    )


def compare_states(local: list[SampleState], incoming: SampleState) -> list[dict[str, Any]]:
    return json_diff([state_value(state) for state in local], [state_value(incoming)], "sample")


def restore_branch(run_id: str, branch_id: str, token: str):
    store = ReviewStore()
    if not store.path.exists():
        raise ValueError("Không tìm thấy nhánh đã lưu.")
    with closing(sqlite3.connect(store.path, timeout=10)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        current = local_states(run_id, connection)
        if local_token(current) != token:
            raise ReviewConflict("Mẫu local đã thay đổi. Hãy tải lại và so sánh nhánh.")
        target = next(
            (
                branch
                for branch in saved_branches(run_id, connection)
                if branch.branch_id == branch_id
            ),
            None,
        )
        if target is None:
            raise ValueError("Không tìm thấy nhánh đã lưu.")
        write_active(connection, target, current, restore=True)
