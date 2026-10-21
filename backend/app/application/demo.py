"""Read exported recordings as immutable demo scenarios. Never invokes a provider."""

import hashlib
import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.api.schemas.projects import ProjectResponse, StoryDraft
from app.api.schemas.story import (
    AnalysisResponse,
    EvaluationResponse,
    GenerateResponse,
    IdeaRequest,
)
from app.application.dataset_sources import exported_values

logger = logging.getLogger(__name__)


class ModelUse(BaseModel):
    provider: str
    model: str


class DemoAnswer(BaseModel):
    question: str
    answer: str


class DemoStep(BaseModel):
    kind: Literal["brief", "analysis", "answers", "plan", "evaluation", "edit", "review"]
    title: str
    description: str = ""
    source_run_id: str | None = None
    models_used: list[ModelUse] = Field(default_factory=list)
    idea: str | None = None
    constraints: list[str] = Field(default_factory=list)
    analysis: AnalysisResponse | None = None
    answers: list[DemoAnswer] = Field(default_factory=list)
    draft: StoryDraft | None = None
    feedback: EvaluationResponse | None = None


class DemoSummary(BaseModel):
    id: str
    title: str
    description: str
    started_at: str
    review_status: str
    models_used: list[ModelUse]
    step_count: int


class DemoScenario(DemoSummary):
    steps: list[DemoStep]


class RecordedCall(BaseModel):
    stage: str
    status: str
    provider: str
    model: str | None = None


class Recording(BaseModel):
    schema_version: Literal[1]
    run_id: str = Field(min_length=1)
    operation: Literal["analyze", "plan", "review", "generate"]
    status: Literal["completed"]
    workflow_complete: bool = False
    project_id: str | None = None
    parent_run_id: str | None = None
    source_analysis_id: str | None = None
    started_at: str
    review_status: str = "unreviewed"
    input: dict[str, Any]
    output: dict[str, Any]
    steps: list[RecordedCall]


def _read_recordings(values: Iterable[dict[str, Any]] | None = None) -> dict[str, Recording]:
    records: dict[str, Recording] = {}
    conflicts: set[str] = set()
    for value in exported_values() if values is None else values:
        try:
            record = Recording.model_validate(value)
            expected = {
                "analyze": {"reasoning"},
                "plan": {"planning", "evaluation"},
                "review": {"evaluation"},
                "generate": {"reasoning", "planning", "evaluation"},
            }
            if not expected[record.operation].issubset(
                {call.stage for call in record.steps}
            ) or any(call.status != "completed" for call in record.steps):
                continue
            if record.operation == "analyze":
                analysis = ProjectResponse.model_validate(record.output)
                if analysis.id != record.project_id or analysis.analysis is None:
                    continue
        except (ValueError, ValidationError):
            continue
        if record.run_id in conflicts:
            continue
        previous = records.get(record.run_id)
        if previous is not None and previous != record:
            logger.warning("Conflicting demo recording id=%s", record.run_id)
            records.pop(record.run_id)
            conflicts.add(record.run_id)
            continue
        records[record.run_id] = record
    return records


def _models(record: Recording | None, stage: str) -> list[ModelUse]:
    if record is None:
        return []
    return [
        ModelUse(provider=provider, model=model)
        for provider, model in dict.fromkeys(
            (call.provider, call.model)
            for call in record.steps
            if call.stage == stage and call.status == "completed" and call.model
        )
    ]


def _project_pair(record: Recording) -> tuple[ProjectResponse, ProjectResponse]:
    before = ProjectResponse.model_validate(record.input)
    after = ProjectResponse.model_validate(record.output)
    if (
        record.project_id != before.id
        or before.id != after.id
        or before.idea != after.idea
        or before.constraints != after.constraints
        or before.analysis is None
        or after.analysis is None
        or before.analysis.artifact_id != after.analysis.artifact_id
        or record.source_analysis_id != before.analysis.artifact_id
        or after.draft is None
        or after.feedback is None
        or not after.feedback_is_current
    ):
        raise ValueError("Recording does not contain a consistent saved story round.")
    if record.operation == "review" and before.draft != after.draft:
        raise ValueError("Review must not rewrite the recorded draft.")
    return before, after


def _initial_steps(root: Recording, records: dict[str, Recording]) -> list[DemoStep]:
    analysis_record = None
    analysis: AnalysisResponse | None
    draft: StoryDraft | None
    feedback: EvaluationResponse | None
    if root.operation == "generate":
        brief = IdeaRequest.model_validate(root.input)
        output = GenerateResponse.model_validate(root.output)
        idea, constraints, analysis = brief.idea, brief.constraints, output.analysis
        draft = StoryDraft.model_validate(
            output.story_plan.model_dump(exclude={"request_id", "domain_id"})
        )
        feedback, answers = output.evaluation, []
        analysis_record = root
        answer_description = "Luồng này đã tạo bản phát triển trực tiếp; không có câu trả lời tác giả riêng."
    else:
        before, after = _project_pair(root)
        idea, constraints, analysis = before.idea, before.constraints, before.analysis
        draft, feedback = after.draft, after.feedback
        answers = [
            DemoAnswer(question=question, answer=answer)
            for question, answer in before.creator_answers()
        ]
        answer_description = "Các lựa chọn tác giả đã gửi khi tạo bản phát triển này."
        if not answers:
            answer_description = "Ý tưởng này không có câu trả lời làm rõ riêng trong bản ghi."
        for candidate in records.values():
            if candidate.operation != "analyze" or candidate.project_id != root.project_id:
                continue
            candidate_analysis = candidate.output.get("analysis") or {}
            if (
                candidate_analysis.get("artifact_id") == root.source_analysis_id
                and analysis is not None
                and candidate_analysis == analysis.model_dump(mode="json")
            ):
                analysis_record = candidate
                break
    return [
        DemoStep(kind="brief", title="Ý tưởng ban đầu", idea=idea, constraints=constraints),
        DemoStep(
            kind="analysis",
            title="Làm rõ ý tưởng",
            analysis=analysis,
            source_run_id=analysis_record.run_id if analysis_record else None,
            models_used=_models(analysis_record, "reasoning"),
        ),
        DemoStep(
            kind="answers",
            title="Lựa chọn của tác giả",
            answers=answers,
            description=answer_description,
            source_run_id=root.run_id,
        ),
        DemoStep(
            kind="plan",
            title="Bản phát triển câu chuyện",
            draft=draft,
            source_run_id=root.run_id,
            models_used=_models(root, "planning"),
        ),
        DemoStep(
            kind="evaluation",
            title="Phản hồi ban đầu",
            draft=draft,
            feedback=feedback,
            source_run_id=root.run_id,
            models_used=_models(root, "evaluation"),
        ),
    ]


def scenarios(records: dict[str, Recording] | None = None) -> list[DemoScenario]:
    if records is None:
        records = _read_recordings()
    children: dict[str, list[Recording]] = defaultdict(list)
    valid_projects = {}
    for record in records.values():
        if record.operation not in {"plan", "review"}:
            continue
        try:
            valid_projects[record.run_id] = _project_pair(record)
        except (ValueError, ValidationError):
            continue
        if record.operation == "review" and record.parent_run_id:
            children[record.parent_run_id].append(record)
    result = []
    for root in sorted(records.values(), key=lambda record: (record.started_at, record.run_id)):
        if root.operation not in {"plan", "generate"} or not root.workflow_complete:
            continue
        try:
            initial = _initial_steps(root, records)
        except (ValueError, ValidationError, AttributeError):
            logger.warning("Skipping incomplete demo scenario id=%s", root.run_id)
            continue
        # Enumerate recorded review branches without borrowing unrelated project revisions.
        paths: list[list[Recording]] = [[]]
        branches = []
        while paths:
            path = paths.pop()
            parent = path[-1] if path else root
            seen = {root.run_id, *(record.run_id for record in path)}
            following = [
                record
                for record in children[parent.run_id]
                if record.run_id not in seen
                and record.project_id == root.project_id
                and record.source_analysis_id == root.source_analysis_id
                and record.input.get("analysis") == root.input.get("analysis")
                and record.input.get("idea") == initial[0].idea
                and record.input.get("constraints") == initial[0].constraints
                and valid_projects[record.run_id][0].revision >= parent.output.get("revision", 0)
            ]
            if following:
                paths.extend([*path, record] for record in following)
            else:
                branches.append(path)
        branches.sort(key=lambda path: [(record.started_at, record.run_id) for record in path])
        for branch_index, branch in enumerate(branches, 1):
            steps = list(initial)
            for index, review in enumerate(branch, 1):
                before, after = valid_projects[review.run_id]
                steps.extend(
                    [
                        DemoStep(
                            kind="edit",
                            title=f"Bản tác giả sửa · lượt {index}",
                            description="Bản chỉnh sửa và lựa chọn đã được ghi trước lượt nhận phản hồi.",
                            draft=before.draft,
                            source_run_id=review.run_id,
                            answers=[
                                DemoAnswer(question=q, answer=a)
                                for q, a in before.creator_answers()
                            ],
                        ),
                        DemoStep(
                            kind="review",
                            title=f"Phản hồi bản sửa · lượt {index}",
                            draft=after.draft,
                            feedback=after.feedback,
                            source_run_id=review.run_id,
                            models_used=_models(review, "evaluation"),
                        ),
                    ]
                )
            models = list(
                {
                    (model.provider, model.model): model
                    for step in steps
                    for model in step.models_used
                }.values()
            )
            evidence = [root, *branch]
            analysis_source = initial[1].source_run_id
            if analysis_source and analysis_source in records:
                evidence.append(records[analysis_source])
            statuses = {record.review_status for record in evidence}
            status = (
                "rejected"
                if "rejected" in statuses
                else "needs_revision"
                if "needs_revision" in statuses
                else "approved"
                if statuses == {"approved"}
                else "unreviewed"
            )
            key = ":".join(record.run_id for record in [root, *branch])
            title = initial[3].draft.title if initial[3].draft else "Câu chuyện đã ghi"
            if len(branches) > 1:
                title += f" · nhánh {branch_index}"
            result.append(
                DemoScenario(
                    id=hashlib.sha256(key.encode()).hexdigest()[:24],
                    title=title,
                    description=(initial[0].idea or "")[:180],
                    started_at=root.started_at,
                    review_status=status,
                    models_used=models,
                    step_count=len(steps),
                    steps=steps,
                )
            )
    return result
