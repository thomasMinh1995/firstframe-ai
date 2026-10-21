"""Human annotations live separately from immutable exported recordings."""

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.api.schemas.story import GenerateResponse
from app.application.dataset import get_dataset_store
from app.application.dataset_corrections import apply_demo_corrections
from app.application.dataset_sources import exported_values
from app.application.demo import _project_pair, _read_recordings, scenarios


class ExportedSample(BaseModel):
    schema_version: Literal[1]
    run_id: str = Field(min_length=1)
    operation: Literal["analyze", "plan", "review", "generate"]
    status: str
    started_at: str
    input: dict[str, Any]
    output: dict[str, Any] | None
    steps: list[dict[str, Any]]
    models_used: list[dict[str, str]] = Field(default_factory=list)


class ReviewFields(BaseModel):
    revision: int = Field(default=0, ge=0)
    status: Literal["unreviewed", "approved", "needs_revision"] = "unreviewed"
    feedback: str = Field(default="", max_length=10000)
    use_for_demo: bool = False
    use_for_training: bool = False
    updated_at: str | None = None


class Review(ReviewFields):
    corrected_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ReviewUpdate(ReviewFields):
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class OutputUpdate(BaseModel):
    revision: int = Field(ge=0)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    corrected_outputs: dict[str, dict[str, Any]]


class RestoreUpdate(BaseModel):
    revision: int = Field(ge=0)
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: int = Field(ge=0)


class OutputVersion(BaseModel):
    version: int
    created_at: str | None
    action: Literal["original", "edit", "restore", "imported"]
    restored_from: int | None = None
    corrected_outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)


class ReviewConflict(Exception):
    pass


def exported_samples() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    for value in exported_values():
        try:
            ExportedSample.model_validate(value)
        except ValidationError:
            continue
        key = value["run_id"]
        if key in conflicts:
            continue
        if key in records and fingerprint(records[key]) != fingerprint(value):
            records.pop(key)
            conflicts.add(key)
        else:
            records[key] = value
    return records


def fingerprint(sample: dict[str, Any]) -> str:
    content = {
        key: value
        for key, value in sample.items()
        if key not in {"review_status", "human_feedback"}
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class ReviewStore:
    def __init__(self) -> None:
        self.path = get_dataset_store().directory / "reviews.sqlite3"

    def reviews(self) -> dict[tuple[str, str], Review]:
        if not self.path.exists():
            return {}
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            if not connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='reviews'"
            ).fetchone():
                return {}
            rows = connection.execute("SELECT run_id, fingerprint, data FROM reviews").fetchall()
        return {(run_id, digest): Review.model_validate_json(data) for run_id, digest, data in rows}

    @staticmethod
    def _versions(connection: sqlite3.Connection, run_id: str, digest: str, current: Review):
        versions = [OutputVersion(version=0, created_at=None, action="original")]
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='output_versions'"
        ).fetchone():
            rows = connection.execute(
                "SELECT data FROM output_versions WHERE run_id=? AND fingerprint=? ORDER BY version",
                (run_id, digest),
            ).fetchall()
            versions.extend(OutputVersion.model_validate_json(row[0]) for row in rows)
        if len(versions) == 1 and current.corrected_outputs:
            versions.append(
                OutputVersion(
                    version=1,
                    created_at=None,
                    action="imported",
                    corrected_outputs=current.corrected_outputs,
                )
            )
        return versions

    def history(self, run_id: str, digest: str) -> list[OutputVersion]:
        if not self.path.exists():
            return [OutputVersion(version=0, created_at=None, action="original")]
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            has_reviews = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='reviews'"
            ).fetchone()
            row = (
                connection.execute(
                    "SELECT data FROM reviews WHERE run_id=? AND fingerprint=?", (run_id, digest)
                ).fetchone()
                if has_reviews
                else None
            )
            current = Review.model_validate_json(row[0]) if row else Review()
            return self._versions(connection, run_id, digest, current)

    def save(
        self, run_id: str, update: ReviewUpdate | OutputUpdate, *, restored_from: int | None = None
    ) -> Review:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS reviews (run_id TEXT, fingerprint TEXT, "
                "data TEXT NOT NULL, PRIMARY KEY (run_id, fingerprint))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS output_versions (run_id TEXT, fingerprint TEXT, "
                "version INTEGER, data TEXT NOT NULL, PRIMARY KEY(run_id, fingerprint, version))"
            )
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='dataset_active_branches'"
            ).fetchone():
                active = connection.execute(
                    "SELECT b.data FROM dataset_active_branches a JOIN dataset_branches b "
                    "ON a.run_id=b.run_id AND a.branch_id=b.branch_id WHERE a.run_id=?",
                    (run_id,),
                ).fetchone()
                if active and json.loads(active[0])["fingerprint"] != update.fingerprint:
                    raise ReviewConflict("Nhánh nguồn đã thay đổi. Hãy tải lại mẫu trước khi lưu.")
            row = connection.execute(
                "SELECT data FROM reviews WHERE run_id=? AND fingerprint=?",
                (run_id, update.fingerprint),
            ).fetchone()
            current = Review.model_validate_json(row[0]) if row else Review()
            if current.revision != update.revision:
                raise ReviewConflict("Đánh giá đã thay đổi ở cửa sổ khác. Hãy tải lại mẫu.")
            if isinstance(update, OutputUpdate):
                versions = self._versions(connection, run_id, update.fingerprint, current)
                if restored_from is not None:
                    target = next(
                        (item for item in versions if item.version == restored_from), None
                    )
                    if target is None or target.corrected_outputs != update.corrected_outputs:
                        raise ReviewConflict(
                            "Phiên bản khôi phục không còn khớp. Hãy tải lại lịch sử."
                        )
                if restored_from is None and update.corrected_outputs == current.corrected_outputs:
                    return current
                values = current.model_dump()
                values.update(
                    corrected_outputs=update.corrected_outputs,
                    status="unreviewed",
                    use_for_demo=False,
                    use_for_training=False,
                )
            else:
                values = update.model_dump(exclude={"fingerprint"})
                values["corrected_outputs"] = current.corrected_outputs
            values.update(revision=current.revision + 1, updated_at=datetime.now(UTC).isoformat())
            review = Review.model_validate(values)
            if isinstance(update, OutputUpdate):
                if versions[-1].action == "imported":
                    legacy = versions[-1]
                    connection.execute(
                        "INSERT OR IGNORE INTO output_versions VALUES (?, ?, ?, ?)",
                        (run_id, update.fingerprint, legacy.version, legacy.model_dump_json()),
                    )
                version = OutputVersion(
                    version=versions[-1].version + 1,
                    created_at=review.updated_at,
                    action="restore" if restored_from is not None else "edit",
                    restored_from=restored_from,
                    corrected_outputs=review.corrected_outputs,
                )
                connection.execute(
                    "INSERT INTO output_versions VALUES (?, ?, ?, ?)",
                    (run_id, update.fingerprint, version.version, version.model_dump_json()),
                )
            connection.execute(
                "INSERT INTO reviews VALUES (?, ?, ?) ON CONFLICT(run_id, fingerprint) "
                "DO UPDATE SET data=excluded.data",
                (run_id, update.fingerprint, review.model_dump_json()),
            )
        return review


def sample_catalog(
    records: dict[str, dict[str, Any]] | None = None,
    reviews: dict[tuple[str, str], Review] | None = None,
) -> list[dict[str, Any]]:
    if records is None:
        records = exported_samples()
    eligible = _read_recordings(records.values())
    if reviews is None:
        reviews = ReviewStore().reviews()
    result = []
    for run_id, sample in records.items():
        digest = fingerprint(sample)
        review = reviews.get((run_id, digest), Review())
        valid = run_id in eligible
        if valid:
            try:
                record = eligible[run_id]
                if record.operation in {"plan", "review"}:
                    _project_pair(record)
                elif record.operation == "generate":
                    GenerateResponse.model_validate(record.output)
            except ValueError:
                valid = False
        if not valid:
            review = review.model_copy(update={"use_for_demo": False, "use_for_training": False})
        output = sample.get("output") or {}
        draft = output.get("draft") or output.get("story_plan")
        title = draft.get("title") if isinstance(draft, dict) else output.get("title")
        title = title if isinstance(title, str) else "Workflow đã ghi"
        idea = sample["input"].get("idea")
        result.append(
            {
                "run_id": run_id,
                "fingerprint": digest,
                "operation": sample["operation"],
                "status": sample.get("status", "unknown"),
                "title": title or "Workflow đã ghi",
                "project_id": sample.get("project_id"),
                "idea": idea if isinstance(idea, str) else "",
                "started_at": sample.get("started_at", ""),
                "models_used": [
                    model
                    for model in sample.get("models_used", [])
                    if "provider" in model and "model" in model
                ],
                "eligible": valid,
                "review": review.model_dump(exclude={"corrected_outputs"}),
                "has_corrections": bool(review.corrected_outputs),
            }
        )
    return sorted(result, key=lambda item: (item["started_at"], item["run_id"]), reverse=True)


def selected_ids(purpose: Literal["demo", "training"], catalog: list[dict[str, Any]]) -> set[str]:
    return {
        sample["run_id"]
        for sample in catalog
        if sample["eligible"]
        and sample["review"]["status"] == "approved"
        and sample["review"][f"use_for_{purpose}"]
    }


def reviewed_scenarios(curated: bool = False):
    records = _read_recordings()
    samples = exported_samples()
    reviews = ReviewStore().reviews()
    catalog = sample_catalog(samples, reviews)
    annotations = {sample["run_id"]: sample["review"] for sample in catalog}
    if curated:
        allowed = selected_ids("demo", catalog)
        records = {key: record for key, record in records.items() if key in allowed}
    for key, record in records.items():
        record.review_status = annotations.get(key, {}).get("status", "unreviewed")
    result = scenarios(records)
    if curated:
        # Saved analysis without its approved source is only suitable for preview.
        result = [
            scenario
            for scenario in result
            if scenario.review_status == "approved"
            and all(step.source_run_id for step in scenario.steps if step.kind == "analysis")
        ]
    corrections = {
        key: review.corrected_outputs
        for (key, digest), review in reviews.items()
        if key in samples and digest == fingerprint(samples[key]) and review.status == "approved"
    }
    for scenario in result:
        apply_demo_corrections(scenario, samples, corrections)
    return result


def training_export() -> str:
    samples = exported_samples()
    reviews = ReviewStore().reviews()
    selected = selected_ids("training", sample_catalog(samples, reviews))
    lines = []
    for run_id in sorted(selected):
        sample = samples[run_id]
        review = reviews[(run_id, fingerprint(sample))]
        corrected_upstream = False
        for index, step in enumerate(sample["steps"]):
            corrected = review.corrected_outputs.get(str(index))
            # Downstream prompts still describe the original upstream output.
            if corrected_upstream:
                continue
            if corrected is not None:
                corrected_upstream = True
            request = step.get("request") or {}
            if not isinstance(request, dict):
                continue
            instructions = request.get("effective_instructions") or request.get("instructions")
            if (
                step.get("status") != "completed"
                or not step.get("model")
                or not isinstance(instructions, str)
                or not isinstance(request.get("input_text"), str)
                or not isinstance(step.get("output"), dict)
            ):
                continue
            lines.append(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": run_id,
                        "step_index": index,
                        "project_id": sample.get("project_id"),
                        "stage": step.get("stage"),
                        "provider": step.get("provider"),
                        "model": step.get("model"),
                        "fingerprint": fingerprint(sample),
                        "review": review.model_dump(exclude={"corrected_outputs"}),
                        "output_source": "human_corrected" if corrected is not None else "model",
                        "original_output": step["output"],
                        "corrected_output": corrected,
                        "response_schema": request.get("response_schema"),
                        "messages": [
                            {"role": "system", "content": instructions},
                            {"role": "user", "content": request["input_text"]},
                            {
                                "role": "assistant",
                                "content": json.dumps(
                                    corrected if corrected is not None else step["output"],
                                    ensure_ascii=False,
                                ),
                            },
                        ],
                    },
                    ensure_ascii=False,
                )
            )
    return "\n".join(lines) + ("\n" if lines else "")
