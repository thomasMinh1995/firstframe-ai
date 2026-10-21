"""Portable approved datasets. Import records, reviews and history in one transaction."""

import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.dataset_branches import (
    BranchReview as BundleReview,
)
from app.application.dataset_branches import (
    BranchVersion as BundleVersion,
)
from app.application.dataset_branches import (
    ConflictChoice,
    SampleState,
    SavedBranch,
    compare_states,
    create_branch_tables,
    digest,
    local_states,
    local_token,
    save_branch,
    saved_branches,
    state_value,
    validate_state,
    write_active,
)
from app.application.dataset_review import (
    ExportedSample,
    Review,
    ReviewConflict,
    ReviewStore,
    exported_samples,
    fingerprint,
    sample_catalog,
)
from app.application.dataset_sources import exported_values
from app.application.demo import _read_recordings, scenarios

MAX_BUNDLE_BYTES = 25 * 1024 * 1024


class BundleEntry(SampleState):
    branches: list[SavedBranch] = Field(default_factory=list, max_length=1000)


class DatasetBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: Literal["firstframe-reviewed-dataset"]
    schema_version: Literal[1, 2]
    created_at: str
    samples: list[BundleEntry] = Field(min_length=1, max_length=1000)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def checksum(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "sha256"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def validate_bundle(value: dict[str, Any]) -> DatasetBundle:
    bundle = DatasetBundle.model_validate(value, strict=True)
    if not hmac.compare_digest(checksum(value), bundle.sha256):
        raise ValueError("Gói bị thay đổi hoặc hỏng: checksum không khớp.")
    records: dict[str, dict[str, Any]] = {}
    reviews: dict[tuple[str, str], Review] = {}
    for entry in bundle.samples:
        sample = entry.recording
        ExportedSample.model_validate(sample, strict=True)
        run_id = sample["run_id"]
        if run_id in records or entry.fingerprint != fingerprint(sample):
            raise ValueError("ID mẫu trùng hoặc fingerprint bản gốc không khớp.")
        if entry.review.status != "approved" or entry.review.revision < 1:
            raise ValueError("Gói chỉ được chứa mẫu đã duyệt.")
        validate_state(entry)
        ids = set()
        for branch in entry.branches:
            validate_state(branch)
            if (
                branch.recording["run_id"] != run_id
                or digest(state_value(branch)) != branch.branch_id
                or branch.branch_id in ids
            ):
                raise ValueError("Nhánh lưu trữ không hợp lệ hoặc không thuộc mẫu.")
            ids.add(branch.branch_id)
        if entry.branches and bundle.schema_version != 2:
            raise ValueError("Gói có nhánh xung đột cần schema version 2.")
        records[run_id] = sample
        reviews[(run_id, entry.fingerprint)] = entry.review
    if not all(item["eligible"] for item in sample_catalog(records, reviews)):
        raise ValueError("Gói chứa workflow chưa hoàn tất hoặc snapshot không hợp lệ.")
    return bundle


def export_bundle() -> dict[str, Any]:
    records = exported_samples()
    store = ReviewStore()
    entries = []
    if store.path.exists():
        with closing(sqlite3.connect(store.path, timeout=10)) as connection, connection:
            connection.execute("BEGIN")
            rows = connection.execute("SELECT run_id, fingerprint, data FROM reviews").fetchall()
            reviews = {
                (run_id, digest): Review.model_validate_json(data) for run_id, digest, data in rows
            }
            for sample in sample_catalog(records, reviews):
                if not sample["eligible"] or sample["review"]["status"] != "approved":
                    continue
                run_id, digest = sample["run_id"], sample["fingerprint"]
                review = reviews[(run_id, digest)]
                entries.append(
                    BundleEntry(
                        recording=records[run_id],
                        fingerprint=digest,
                        review=BundleReview.model_validate(review.model_dump()),
                        history=[
                            BundleVersion.model_validate(version.model_dump())
                            for version in store._versions(connection, run_id, digest, review)
                        ],
                        branches=saved_branches(run_id, connection),
                    )
                )
    if not entries:
        raise ValueError("Chưa có mẫu tốt đã duyệt để xuất.")
    value = {
        "format": "firstframe-reviewed-dataset",
        "schema_version": 2 if any(entry.branches for entry in entries) else 1,
        "created_at": datetime.now(UTC).isoformat(),
        "samples": [
            entry.model_dump(mode="json", exclude={"branches"} if not entry.branches else set())
            for entry in sorted(entries, key=lambda entry: entry.recording["run_id"])
        ],
    }
    value["sha256"] = checksum(value)
    validate_bundle(value)
    if len(json.dumps(value, ensure_ascii=False).encode()) > MAX_BUNDLE_BYTES:
        raise ValueError("Gói vượt giới hạn 25 MiB. Hãy giảm số mẫu đã duyệt trước khi xuất.")
    return value


def inspect_bundle(
    bundle: DatasetBundle, connection: sqlite3.Connection | None = None
) -> dict[str, Any]:
    store = ReviewStore()
    local = list(exported_values())
    if connection is None:
        reviews = store.reviews()
    else:
        has_table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='reviews'"
        ).fetchone()
        rows = (
            connection.execute("SELECT run_id, fingerprint, data FROM reviews").fetchall()
            if has_table
            else []
        )
        reviews = {
            (run_id, digest): Review.model_validate_json(data) for run_id, digest, data in rows
        }
    conflicts = []
    unchanged = []
    for entry in bundle.samples:
        run_id = entry.recording["run_id"]
        matching = [sample for sample in local if sample.get("run_id") == run_id]
        if any(fingerprint(sample) != entry.fingerprint for sample in matching):
            conflicts.append(
                {"run_id": run_id, "reason": "Bản gốc cùng ID có nội dung khác trên máy này."}
            )
            continue
        current = reviews.get((run_id, entry.fingerprint))
        if current is None:
            versions = (
                store._versions(connection, run_id, entry.fingerprint, Review())
                if connection is not None
                else store.history(run_id, entry.fingerprint)
            )
            if len(versions) > 1:
                conflicts.append(
                    {
                        "run_id": run_id,
                        "reason": "Có lịch sử local thiếu trạng thái đánh giá; cần kiểm tra dữ liệu trước.",
                    }
                )
        else:
            versions = (
                store._versions(connection, run_id, entry.fingerprint, current)
                if connection is not None
                else store.history(run_id, entry.fingerprint)
            )
            if current.model_dump(exclude={"revision", "updated_at"}) != entry.review.model_dump(
                exclude={"revision", "updated_at"}
            ) or [v.model_dump() for v in versions] != [v.model_dump() for v in entry.history]:
                conflicts.append(
                    {
                        "run_id": run_id,
                        "reason": "Góp ý, bản sửa hoặc lịch sử trên máy này khác gói nhập.",
                    }
                )
            elif matching:
                unchanged.append(run_id)
    for conflict in conflicts:
        states = local_states(conflict["run_id"], connection)
        conflict["local_token"] = local_token(states)
        conflict["originals_differ"] = any(
            state.fingerprint
            != next(
                entry.fingerprint
                for entry in bundle.samples
                if entry.recording["run_id"] == conflict["run_id"]
            )
            for state in states
        )
        try:
            for state in states:
                validate_state(state)
            conflict["incoming_allowed"] = bool(states)
        except ValueError:
            conflict["incoming_allowed"] = False
    branch_add_count = sum(
        len(
            {branch.branch_id for branch in entry.branches}
            - {branch.branch_id for branch in saved_branches(entry.recording["run_id"], connection)}
        )
        for entry in bundle.samples
    )
    records = {
        entry.recording["run_id"]: entry.recording
        for entry in bundle.samples
        if entry.review.use_for_demo
    }
    playable = scenarios(_read_recordings(records.values()))
    demo_count = sum(
        all(step.source_run_id for step in scenario.steps if step.kind == "analysis")
        for scenario in playable
    )
    return {
        "sha256": bundle.sha256,
        "branch_add_count": branch_add_count,
        "sample_count": len(bundle.samples),
        "new_count": len(bundle.samples) - len(unchanged) - len(conflicts),
        "unchanged_count": len(unchanged),
        "unchanged_ids": unchanged,
        "conflicts": conflicts,
        "correction_count": sum(bool(entry.review.corrected_outputs) for entry in bundle.samples),
        "history_count": sum(len(entry.history) - 1 for entry in bundle.samples),
        "demo_count": demo_count,
    }


def import_bundle(
    bundle: DatasetBundle, resolutions: dict[str, ConflictChoice] | None = None
) -> dict[str, Any]:
    resolutions = resolutions or {}
    report = inspect_bundle(bundle)
    check_resolutions(bundle, report, resolutions)
    store = ReviewStore()
    store.path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(store.path, timeout=10)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        report = inspect_bundle(bundle, connection)
        check_resolutions(bundle, report, resolutions)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS reviews (run_id TEXT, fingerprint TEXT, data TEXT NOT NULL, PRIMARY KEY(run_id, fingerprint))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS output_versions (run_id TEXT, fingerprint TEXT, version INTEGER, data TEXT NOT NULL, PRIMARY KEY(run_id, fingerprint, version))"
        )
        connection.execute(
            "CREATE TABLE IF NOT EXISTS imported_samples (run_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        if report["conflicts"] or any(entry.branches for entry in bundle.samples):
            create_branch_tables(connection)
        conflicts = {item["run_id"]: item for item in report["conflicts"]}
        kept = 0
        replaced = 0
        for entry in bundle.samples:
            run_id = entry.recording["run_id"]
            for branch in entry.branches:
                connection.execute(
                    "INSERT OR IGNORE INTO dataset_branches VALUES (?, ?, ?)",
                    (run_id, branch.branch_id, branch.model_dump_json()),
                )
            if run_id in conflicts:
                states = local_states(run_id, connection)
                save_branch(connection, entry, "incoming")
                if resolutions[run_id].choice == "local":
                    for state in states:
                        try:
                            validate_state(state)
                        except ValueError:
                            continue
                        save_branch(connection, state, "local")
                    kept += 1
                else:
                    write_active(connection, entry, states)
                    replaced += 1
                continue
            if run_id in report["unchanged_ids"]:
                continue
            connection.execute(
                "INSERT OR IGNORE INTO imported_samples VALUES (?, ?)",
                (run_id, json.dumps(entry.recording, ensure_ascii=False)),
            )
            connection.execute(
                "INSERT OR IGNORE INTO reviews VALUES (?, ?, ?)",
                (run_id, entry.fingerprint, entry.review.model_dump_json()),
            )
            for version in entry.history[1:]:
                connection.execute(
                    "INSERT OR IGNORE INTO output_versions VALUES (?, ?, ?, ?)",
                    (run_id, entry.fingerprint, version.version, version.model_dump_json()),
                )
    return {**report, "kept_local_count": kept, "used_incoming_count": replaced}


def check_resolutions(
    bundle: DatasetBundle, report: dict[str, Any], resolutions: dict[str, ConflictChoice]
):
    conflicts = {item["run_id"]: item for item in report["conflicts"]}
    if set(resolutions) - set(conflicts):
        raise ReviewConflict("Xung đột đã thay đổi. Hãy xem trước và chọn lại từng mẫu.")
    if set(conflicts) - set(resolutions):
        raise ReviewConflict("Hãy chọn giữ local hoặc bản nhập cho từng mẫu xung đột.")
    for run_id, choice in resolutions.items():
        if choice.local_token != conflicts[run_id]["local_token"]:
            raise ReviewConflict(
                "Dữ liệu local đã thay đổi sau khi so sánh. Hãy tải lại phần xem trước."
            )
        if choice.choice == "incoming" and not conflicts[run_id]["incoming_allowed"]:
            raise ReviewConflict(
                "Bản local không đủ dữ liệu để lưu trọn lịch sử; hãy giữ local và kiểm tra dữ liệu."
            )


def compare_conflict(bundle: DatasetBundle, run_id: str):
    entry = next((entry for entry in bundle.samples if entry.recording["run_id"] == run_id), None)
    if entry is None:
        raise ValueError("Mẫu không thuộc gói nhập.")
    states = local_states(run_id)
    return {
        "run_id": run_id,
        "local_token": local_token(states),
        "changes": compare_states(states, entry),
        "local_history_counts": [len(state.history) - 1 for state in states],
        "incoming_history_count": len(entry.history) - 1,
    }
