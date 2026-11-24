"""Validate editorial outputs and project them onto read-only demo snapshots."""

import json
from typing import Any

from pydantic import BaseModel

from app.application.ai_provider import MalformedProviderResponseError
from app.application.demo import DemoScenario
from app.application.workflow import (
    _evaluation_findings,
    _EvaluationOutput,
    _PlanningOutput,
    _ReasoningOutput,
    _RevisionReviewOutput,
    revision_evaluation,
    _structured_plan_sections,
)

OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "reasoning": _ReasoningOutput,
    "planning": _PlanningOutput,
    "evaluation": _EvaluationOutput,
}


def card_review_context(step: dict) -> dict:
    try:
        text = step["request"]["input_text"].rsplit("Card review context (JSON data):\n", 1)[1]
        return json.JSONDecoder().raw_decode(text)[0]
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError("Thiếu nguồn đối chiếu card trong bản ghi.") from error


def _recorded_id_allows(value: str | None, schema: dict) -> bool:
    if "anyOf" in schema:
        return any(_recorded_id_allows(value, item) for item in schema["anyOf"])
    if "const" in schema:
        return value == schema["const"]
    if "enum" in schema:
        return value in schema["enum"]
    return value is None if schema.get("type") == "null" else isinstance(value, str)


def _validate_recorded_card_shape(output: _RevisionReviewOutput, raw: dict, schema: dict) -> None:
    # Recorded calls can allow three reviews or different card IDs; keep their original contract.
    properties = schema["properties"]
    reviews = properties["reviews"]
    if (not set(schema.get("required", [])).issubset(raw)
            or not reviews.get("minItems", 1) <= len(output.reviews) <= reviews.get("maxItems", 3)):
        raise ValueError("Output không khớp số nhận xét hoặc trường bắt buộc của bản ghi.")
    score = properties["rubric_scores"]
    if (score.get("type") == "null" and output.rubric_scores is not None
            or "$ref" in score and output.rubric_scores is None):
        raise ValueError("Điểm không khớp schema của bản ghi.")
    item = reviews["items"]
    fields = schema.get("$defs", {}).get(item.get("$ref", "").rsplit("/", 1)[-1], item)["properties"]
    for review in output.reviews:
        if any(not _recorded_id_allows(getattr(review, key), fields[key])
               for key in ("card_id", "decision_id", "related_card_id")):
            raise ValueError("ID đối chiếu không khớp schema của bản ghi.")


def validate_corrections(
    sample: dict[str, Any], corrections: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    result = {}
    for key, output in corrections.items():
        if not key.isdecimal() or str(int(key)) != key or int(key) >= len(sample["steps"]):
            raise ValueError("Bước output không tồn tại trong mẫu.")
        step = sample["steps"][int(key)]
        model = OUTPUT_MODELS.get(step.get("stage"))
        if step.get("stage") == "evaluation" and "reviews" in step.get("request", {}).get("response_schema", {}).get("properties", {}):
            model = _RevisionReviewOutput
        if sample["status"] != "completed" or step.get("status") != "completed" or model is None:
            raise ValueError("Chỉ sửa output của bước đã hoàn tất và có cấu trúc được hỗ trợ.")
        parsed = model.model_validate(output, strict=True)
        if isinstance(parsed, _RevisionReviewOutput):
            _validate_recorded_card_shape(parsed, output, step["request"]["response_schema"])
            try:
                revision_evaluation(parsed, card_review_context(step))
            except MalformedProviderResponseError as error:
                raise ValueError("Card hoặc lựa chọn đối chiếu không hợp lệ.") from error
        validated = parsed.model_dump(mode="json")
        if validated != step.get("output"):
            result[key] = validated
    return result


def apply_demo_corrections(
    scenario: DemoScenario,
    samples: dict[str, dict[str, Any]],
    corrections: dict[str, dict[str, dict[str, Any]]],
) -> None:
    for step in scenario.steps:
        source = step.source_run_id
        if source not in samples or source not in corrections:
            continue
        edits = {
            samples[source]["steps"][int(index)]["stage"]: output
            for index, output in corrections[source].items()
        }
        edited = False
        if step.analysis is not None and "reasoning" in edits:
            output = _ReasoningOutput.model_validate(edits["reasoning"])
            step.analysis = type(step.analysis).model_validate(
                {
                    **step.analysis.model_dump(),
                    "summary": output.summary,
                    "notes": [note.model_dump() for note in output.notes],
                    "missing_information": output.missing_information,
                    "ai_suggestions": output.ai_suggestions,
                }
            )
            edited = True
        if step.draft is not None and "planning" in edits:
            plan = _PlanningOutput.model_validate(edits["planning"]).story_plan
            step.draft = type(step.draft).model_validate(
                {
                    "title": plan.working_title.title,
                    "logline": plan.logline.text,
                    "sections": [
                        {"title": item.title, "purpose": item.purpose, "content": item.content}
                        for item in _structured_plan_sections(plan)
                    ],
                }
            )
            if step.kind == "plan":
                branch = scenario.title.partition(" · nhánh ")
                scenario.title = plan.working_title.title + (
                    branch[1] + branch[2] if branch[1] else ""
                )
            edited = True
        if step.feedback is not None and "evaluation" in edits:
            if "reviews" in edits["evaluation"]:
                source_step = next(item for item in samples[source]["steps"] if item["stage"] == "evaluation")
                evaluation = revision_evaluation(_RevisionReviewOutput.model_validate(edits["evaluation"]),
                                                 card_review_context(source_step))
            else:
                evaluation = _EvaluationOutput.model_validate(edits["evaluation"])
            step.feedback = type(step.feedback).model_validate(
                {
                    "artifact_id": step.feedback.artifact_id,
                    "passed": evaluation.passed,
                    "rubric_scores": evaluation.rubric_scores.model_dump() if evaluation.rubric_scores else {},
                    "findings": [
                        {
                            "criterion_id": item.criterion_id,
                            "message": item.message,
                            "severity": item.severity,
                            "score": item.score,
                        }
                        for item in _evaluation_findings(evaluation)
                    ],
                }
            )
            edited = True
        elif step.feedback is not None and "planning" in edits:
            step.feedback = None
            step.description += (
                " Phản hồi AI gốc được ẩn vì plan đã được biên tập; chưa có đánh giá cho bản mới."
            )
        if edited:
            step.description += " Đang xem output do người biên tập sửa. Các đầu vào và lựa chọn ở lượt tiếp theo giữ nguyên bản ghi gốc."
