"""Validate editorial outputs and project them onto read-only demo snapshots."""

from typing import Any

from pydantic import BaseModel

from app.application.demo import DemoScenario
from app.application.workflow import (
    _evaluation_findings,
    _EvaluationOutput,
    _format_grounded_evaluation,
    _GroundedEvaluationOutput,
    _GuidedReasoningOutput,
    _PlanningOutput,
    _ReasoningOutput,
    _render_questions,
    _structured_plan_sections,
)

OUTPUT_MODELS: dict[str, type[BaseModel]] = {
    "reasoning": _ReasoningOutput,
    "planning": _PlanningOutput,
    "evaluation": _EvaluationOutput,
}


def validate_corrections(
    sample: dict[str, Any], corrections: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    result = {}
    for key, output in corrections.items():
        if not key.isdecimal() or str(int(key)) != key or int(key) >= len(sample["steps"]):
            raise ValueError("Bước output không tồn tại trong mẫu.")
        step = sample["steps"][int(key)]
        model = OUTPUT_MODELS.get(step.get("stage"))
        if sample["status"] != "completed" or step.get("status") != "completed" or model is None:
            raise ValueError("Chỉ sửa output của bước đã hoàn tất và có cấu trúc được hỗ trợ.")
        if (step.get("stage") == "evaluation"
                and step.get("request", {}).get("response_schema", {}).get("title")
                == "_GroundedEvaluationOutput"):
            model = _GroundedEvaluationOutput
        if (step.get("stage") == "reasoning"
                and step.get("request", {}).get("response_schema", {}).get("title")
                == "_GuidedReasoningOutput"):
            model = _GuidedReasoningOutput
        validated = model.model_validate(output, strict=True).model_dump(mode="json", exclude_unset=True)
        if model is _GroundedEvaluationOutput:
            for original, item in zip(output.get("weaknesses", []), validated["weaknesses"], strict=True):
                if "kind" not in original:
                    item.pop("kind", None)
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
            recorded = next(item for item in samples[source]["steps"] if item["stage"] == "reasoning")
            request = recorded.get("request", {})
            if request.get("response_schema", {}).get("title") == "_GuidedReasoningOutput":
                guided = _GuidedReasoningOutput.model_validate(edits["reasoning"])
                language = "Vietnamese" if "Target response language: Vietnamese" in request.get("input_text", "") else "English"
                output = _ReasoningOutput(summary=guided.summary, notes=guided.notes,
                                          missing_information=_render_questions(guided, language))
            else:
                output = _ReasoningOutput.model_validate(edits["reasoning"])
            step.analysis = type(step.analysis).model_validate(
                {
                    **step.analysis.model_dump(),
                    "summary": output.summary,
                    "notes": [note.model_dump() for note in output.notes],
                    "missing_information": output.missing_information,
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
            evaluation_step = next(item for item in samples[source]["steps"]
                                   if item["stage"] == "evaluation")
            if (evaluation_step.get("request", {}).get("response_schema", {}).get("title")
                    == "_GroundedEvaluationOutput"):
                evaluation = _format_grounded_evaluation(
                    _GroundedEvaluationOutput.model_validate(edits["evaluation"]),
                    "Vietnamese" if "Target response language: Vietnamese" in
                    evaluation_step.get("request", {}).get("input_text", "") else "English",
                )
            else:
                evaluation = _EvaluationOutput.model_validate(edits["evaluation"])
            step.feedback = type(step.feedback).model_validate(
                {
                    "artifact_id": step.feedback.artifact_id,
                    "passed": evaluation.passed,
                    "rubric_scores": evaluation.rubric_scores.model_dump(),
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
