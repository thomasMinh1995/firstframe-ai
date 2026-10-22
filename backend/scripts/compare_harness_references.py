"""Paired, local-only reference-contract experiment; never opens project/dataset stores."""

import argparse
import hashlib
import json
import platform
import random
import re
import secrets
import subprocess
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import Field, ValidationError, create_model

from app.application import workflow
from app.application.ai_provider import (
    MalformedProviderResponseError,
    ProviderMetadata,
    StructuredRequest,
    strict_json_instructions,
)

if not hasattr(workflow, "_GroundedEvaluationOutput"):
    raise SystemExit(
        "This historical experiment requires source commit e5198db. "
        "See docs/evaluations/harness-qwen3b-vs7b-2026-10-22.md for the frozen-source command."
    )

from app.application.workflow import (
    _context_strings,
    _creator_input,
    _grounded_evaluation,
    _GroundedEvaluationOutput,
    _GroundedStrength,
    _GroundedWeakness,
    _LLMPlanningArtifact,
    _planning_input,
    _PlanningOutput,
    _structured_plan_sections,
    create_story_generation_service,
)
from app.core.artifacts import ArtifactMetadata, Constraint, PlanSection

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "demo/evaluations/harness-reference-cases.json"
VARIANTS = ("baseline", "target_keys")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


class CapturedRequest(Exception):
    def __init__(self, request):
        self.request = request


class CaptureProvider:
    def __init__(self, model):
        self.metadata = ProviderMetadata("ollama", model)

    def request_structured(self, request):
        raise CapturedRequest(request)


def constraints(case):
    return tuple(Constraint(str(i), value) for i, value in enumerate(case["constraints"]))


def planning_request(case, model):
    # Capture the actual application request, including its model-specific prompt profile.
    try:
        create_story_generation_service(CaptureProvider(model)).plan(
            case["idea"], tuple(tuple(pair) for pair in case.get("answers", [])),
            constraints(case), response_language=case["language"],
        )
    except CapturedRequest as captured:
        return captured.request
    raise AssertionError("Planning did not request a model response")


def planning_artifact(case, plan_output=None):
    context = _creator_input(
        case["idea"], constraints(case), tuple(tuple(pair) for pair in case.get("answers", []))
    )
    if plan_output is None:
        title, logline = case["title"], case["logline"]
        sections = tuple(PlanSection(str(i), **section) for i, section in enumerate(case["sections"]))
    else:
        plan = _PlanningOutput.model_validate(plan_output).story_plan
        title, logline = plan.working_title.title, plan.logline.text
        sections = tuple(_structured_plan_sections(plan))
    return _LLMPlanningArtifact(
        metadata=ArtifactMetadata(case["id"], "short-film", "planning"),
        source_reasoning_id=case["id"], title=title, logline=logline, sections=sections,
        creator_context=context,
        target_response_language="Vietnamese" if case["language"] == "vi" else "English",
    )


def review_request(planning, model):
    try:
        create_story_generation_service(CaptureProvider(model))._harness.review(planning)
    except CapturedRequest as captured:
        return captured.request
    raise AssertionError("Review did not request a model response")


def snapshot(planning):
    value = {"draft": json.loads(_planning_input(planning)),
             "creator_context": json.loads(planning.creator_context),
             "language": planning.target_response_language}
    value["sha256"] = digest(value)
    prefix = value["sha256"][:12]
    entries = [("title", "title", planning.title), ("logline", "logline", planning.logline)]
    entries.extend((f"section-{i + 1}", section.title, section.content)
                   for i, section in enumerate(planning.sections))
    value["targets"] = [
        {"key": f"{prefix}:{key}", "label": label, "content": content,
         "source": key}
        for key, label, content in entries
    ]
    return value


def candidate_request(request, source):
    keys = Literal[tuple(item["key"] for item in source["targets"])]
    strength = create_model("TargetStrength", __base__=_GroundedStrength, section=(keys, ...))
    weakness = create_model("TargetWeakness", __base__=_GroundedWeakness, section=(keys, ...))
    response_model = create_model(
        "TargetEvaluation", __base__=_GroundedEvaluationOutput,
        strengths=(list[strength], Field(max_length=2)),
        weaknesses=(list[weakness], Field(max_length=3)),
    )
    instructions = request.instructions
    replacements = {
        "section là tên phần thật (hoặc title/logline)":
            "section là khóa mục tiêu trong target_keys (không phải tên phần)",
        "section và quote lấy từ bản HIỆN TẠI.":
            "section lấy từ target_keys; quote lấy từ đúng mục của bản HIỆN TẠI.",
        "section is an actual section title (or title/logline)":
            "section is a target_keys key (not a section title)",
        "section and quote come from the CURRENT draft.":
            "section comes from target_keys; quote comes from that target in the CURRENT draft.",
    }
    changes = 0
    for old, new in replacements.items():
        if old in instructions:
            instructions = instructions.replace(old, new)
            changes += 1
    if changes != 2:
        raise ValueError("Critic reference instructions changed; inspect the candidate adaptation")
    mapping = [{k: item[k] for k in ("key", "label", "source")} for item in source["targets"]]
    anchor = "Compare this draft to the creator facts above before craft advice. "
    if request.input_text.count(anchor) != 1:
        raise ValueError("Critic input changed; inspect the candidate adaptation")
    input_text = request.input_text.replace(
        anchor, "target_keys (source section-N is the Nth section, counted from 1):\n"
        + json.dumps(mapping, ensure_ascii=False) + "\n\n" + anchor,
    ).replace("Copy section names and quote text exactly",
              "Copy the target_keys key into section and quote text exactly")
    return StructuredRequest(instructions, input_text, response_model, "evaluation")


def validate_feedback(output, planning, source, variant, expected_snapshot):
    if source["sha256"] != expected_snapshot:
        raise ValueError("Feedback belongs to a different snapshot")
    if variant == "target_keys":
        # Reuse production quote/author validation with unambiguous, snapshot-scoped titles.
        planning = replace(planning, title="", logline="", sections=tuple(
            PlanSection(item["key"], item["key"], "", item["content"])
            for item in source["targets"]
        ))
    return _grounded_evaluation(_GroundedEvaluationOutput.model_validate(output), planning)


def feedback_errors(output, planning, source, variant):
    sources = ({item["key"]: item["content"] for item in source["targets"]}
               if variant == "target_keys" else
               {**{s.title: s.content for s in planning.sections},
                "title": planning.title, "logline": planning.logline})
    author = list(_context_strings(json.loads(planning.creator_context)))
    errors = []
    for group in ("strengths", "weaknesses"):
        for i, item in enumerate(output[group]):
            if item["section"] not in sources:
                errors.append({"kind": "target_reference", "item": f"{group}.{i}"})
            elif item["quote"] not in sources[item["section"]]:
                errors.append({"kind": "draft_quote", "item": f"{group}.{i}"})
            if group == "weaknesses":
                if item["kind"] == "contradiction" and not item["author_quote"]:
                    errors.append({"kind": "missing_author_quote", "item": f"{group}.{i}"})
                elif item["author_quote"] and not any(item["author_quote"] in part for part in author):
                    errors.append({"kind": "author_quote", "item": f"{group}.{i}"})
    return errors


def call_model(client, request, model, seed):
    schema = request.response_model.model_json_schema()
    instructions = strict_json_instructions(request)
    row = {"started_at": datetime.now(UTC).isoformat(), "stage": request.stage,
           "request": {"instructions": instructions, "input_text": request.input_text,
                       "response_schema": schema, "prompt_sha256": digest(instructions),
                       "input_sha256": digest(request.input_text), "schema_sha256": digest(schema)},
           "raw_output": None, "output": None, "schema_valid": False,
           "runtime_accepted": False, "errors": []}
    started = time.monotonic()
    try:
        response = client.post("/api/chat", json={
            "model": model, "stream": False, "keep_alive": "30m",
            "messages": [{"role": "system", "content": instructions},
                         {"role": "user", "content": request.input_text}],
            "format": schema, "options": {"temperature": 0.3, "num_ctx": 16384, "seed": seed},
        })
        response.raise_for_status()
        payload = response.json()
        row["actual_model"] = payload.get("model")
        row["raw_output"] = payload.get("message", {}).get("content")
        row["timing"] = {key: payload.get(key) for key in (
            "total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration",
            "eval_count", "eval_duration", "done_reason",
        )}
        if row["actual_model"] != model:
            row["errors"].append({"kind": "model_mismatch"})
        elif payload.get("done") is not True or payload.get("error") or payload.get("done_reason") == "length":
            row["errors"].append({"kind": "incomplete_response"})
        else:
            parsed = request.response_model.model_validate_json(row["raw_output"])
            row.update(output=parsed.model_dump(mode="json"), schema_valid=True)
    except ValidationError as error:
        row["errors"].append({"kind": "schema", "details": error.errors(include_url=False)})
        # Retain structurally readable outputs even when an enum is invalid.
        if request.stage == "evaluation":
            try:
                row["output"] = _GroundedEvaluationOutput.model_validate_json(row["raw_output"]).model_dump(mode="json")
            except (ValueError, TypeError):
                pass
    except httpx.TimeoutException as error:
        row["errors"].append({"kind": "timeout", "exception": type(error).__name__})
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as error:
        row["errors"].append({"kind": "provider", "exception": type(error).__name__})
    row["seconds"] = round(time.monotonic() - started, 3)
    return row


def evaluate(client, request, model, seed, planning, source, variant):
    row = call_model(client, request, model, seed)
    if row["output"] is not None:
        row["errors"].extend(feedback_errors(row["output"], planning, source, variant))
        if row["schema_valid"]:
            try:
                validate_feedback(row["output"], planning, source, variant, source["sha256"])
                row["runtime_accepted"] = True
            except MalformedProviderResponseError:
                assert row["errors"], "Production validator rejected an unclassified error"
    return row


def summarize(report):
    result = {}
    for variant in VARIANTS:
        rows = [row for row in report["results"] if row.get("variant") == variant]
        result[variant] = {
            "attempts": len(rows), "schema_valid": sum(row["schema_valid"] for row in rows),
            "runtime_accepted": sum(row["runtime_accepted"] for row in rows),
            "upstream_planning_failures": sum(not row["schema_valid"] for row in report["plans"]),
            "seconds": round(sum(row["seconds"] for row in rows), 3),
            "error_runs": {kind: sum(any(e["kind"] == kind for e in row["errors"]) for row in rows)
                           for kind in sorted({e["kind"] for row in rows for e in row["errors"]})},
        }
    return result


def check_run_integrity(report, output_path):
    errors = []
    try:
        unchanged_source = source_hashes() == report["source_sha256"]
    except OSError:
        unchanged_source = False
    if not unchanged_source:
        errors.append("Source changed during the run")
    if "model_metadata_end" in report:
        final = report["model_metadata_end"]
        expected = report["model_metadata"].get("digest")
        if not expected or not final or final.get("digest") != expected:
            errors.append("Model digest changed or disappeared during the run")
    if any(error["kind"] == "model_mismatch"
           for row in [*report["plans"], *report["results"]] for error in row["errors"]):
        errors.append("Provider returned a different model")
    if errors:
        report.update(status="invalid", integrity_errors=errors,
                      finished_at=datetime.now(UTC).isoformat(), summary=summarize(report))
        save(output_path, report)
        raise ValueError("Invalid experiment: " + "; ".join(errors))


def run(args):
    cases = json.loads(args.cases.read_text())
    if args.case_ids:
        cases = [case for case in cases if case["id"] in args.case_ids]
        if {case["id"] for case in cases} != set(args.case_ids):
            raise ValueError("Unknown case ID")
    if not cases or len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Cases must have unique IDs")
    if len(set(args.seeds)) != len(args.seeds):
        raise ValueError("Seeds must be unique")
    frozen = {"model": args.model, "seeds": args.seeds, "cases": cases,
              "temperature": 0.3, "num_ctx": 16384, "timeout_seconds": args.timeout}
    profile_model = getattr(args, "request_profile_model", None) or args.model
    if profile_model != args.model:
        frozen["request_profile_model"] = profile_model
    if args.resume:
        report = json.loads(args.output.read_text())
        if report.get("status") == "invalid":
            raise ValueError("Invalid experiment cannot be resumed; use a new output path")
        if report["configuration"] != frozen:
            raise ValueError("Resume configuration differs")
        if report["source_sha256"] != source_hashes():
            raise ValueError("Source changed; start a new report")
    else:
        if args.output.exists():
            raise FileExistsError("Report exists; use --resume or a new output path")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = {"configuration": frozen, "source_sha256": source_hashes(),
                  "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  "started_at": datetime.now(UTC).isoformat(), "platform": platform.platform(),
                  "status": "running", "plans": [], "results": [], "summary": {},
                  "semantic_review": "pending; schema validity is not content quality"}
    with httpx.Client(base_url="http://127.0.0.1:11434", timeout=args.timeout, trust_env=False) as client:
        available = client.get("/api/tags").raise_for_status().json()["models"]
        metadata = next((item for item in available if item["name"] == args.model), None)
        if metadata is None:
            raise ValueError("Requested model is not installed; no models are downloaded")
        if args.resume and metadata != report["model_metadata"]:
            raise ValueError("Model metadata changed")
        report["model_metadata"] = metadata
        report.setdefault("load_at_start", client.get("/api/ps").raise_for_status().json())
        save(args.output, report)
        for case_index, case in enumerate(cases):
            for seed_index, seed in enumerate(args.seeds):
                check_run_integrity(report, args.output)
                parent = None
                if case["operation"] == "plan":
                    parent = next((row for row in report["plans"] if row["case_id"] == case["id"] and row["seed"] == seed), None)
                    if parent is None:
                        parent = call_model(client, planning_request(case, profile_model), args.model, seed)
                        parent.update(case_id=case["id"], seed=seed)
                        report["plans"].append(parent)
                        save(args.output, report)
                        check_run_integrity(report, args.output)
                        print(f"{case['id']} seed={seed} planning schema={parent['schema_valid']} {parent['seconds']}s", flush=True)
                    if not parent["schema_valid"]:
                        continue
                planning = planning_artifact(case, parent["output"] if parent else None)
                source = snapshot(planning)
                baseline = review_request(planning, profile_model)
                candidate = candidate_request(baseline, source)
                for variant in VARIANTS[::1 if (case_index + seed_index) % 2 == 0 else -1]:
                    if any(row["case_id"] == case["id"] and row["seed"] == seed and row["variant"] == variant for row in report["results"]):
                        continue
                    request = baseline if variant == "baseline" else candidate
                    row = evaluate(client, request, args.model, seed, planning, source, variant)
                    row.update(case_id=case["id"], seed=seed, variant=variant,
                               operation=case["operation"], snapshot=source)
                    report["results"].append(row)
                    report["summary"] = summarize(report)
                    save(args.output, report)
                    check_run_integrity(report, args.output)
                    print(f"{case['id']} seed={seed} {variant} accepted={row['runtime_accepted']} "
                          f"{row['seconds']}s errors={[e['kind'] for e in row['errors']]}", flush=True)
        report["model_metadata_end"] = next((item for item in client.get("/api/tags").raise_for_status().json()["models"] if item["name"] == args.model), None)
    check_run_integrity(report, args.output)
    report["status"] = "completed"
    report["finished_at"] = datetime.now(UTC).isoformat()
    report["summary"] = summarize(report)
    save(args.output, report)
    return report


def source_hashes():
    paths = [Path(__file__), ROOT / "backend/app/application/workflow.py",
             ROOT / "backend/app/application/ai_provider.py",
             ROOT / "backend/app/application/prompt_loader.py",
             ROOT / "backend/app/application/language.py",
             ROOT / "backend/app/application/knowledge_loader.py"]
    paths += sorted((ROOT / "domains/short-film").rglob("*.md"))
    paths += sorted((ROOT / "domains/short-film").rglob("*.json"))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def blinded_review(report):
    rows = []
    review_key = {}
    for row in report["results"]:
        output = row["output"]
        if output is None:
            continue
        output = json.loads(json.dumps(output))
        labels = {item["key"]: item["label"] for item in row["snapshot"]["targets"]}
        anchors = labels if row["variant"] == "target_keys" else {
            label: label for label in labels.values()
        }
        for item in [*output["strengths"], *output["weaknesses"]]:
            item["section"] = anchors.get(item["section"], "[unavailable target]")
            for field, value in item.items():
                if isinstance(value, str):
                    item[field] = re.sub(
                        r"[0-9a-f]{12}:(?:section-\d+|title|logline)\b",
                        lambda match, labels=labels: labels.get(
                            match.group(), "[unavailable target]"), value,
                    )
        review_id = secrets.token_hex(16)
        review_key[review_id] = {key: row[key] for key in ("case_id", "seed", "variant")}
        rows.append({"review_id": review_id,
                     "case_id": row["case_id"], "source": row["snapshot"]["draft"],
                     "creator_context": row["snapshot"]["creator_context"], "output": output})
    random.SystemRandom().shuffle(rows)
    return rows, review_key


def export_blinded_review(report, output_path):
    blinded_path = output_path.with_suffix(".blinded.json")
    key_path = output_path.with_suffix(".review-key.json")
    if blinded_path.exists() and key_path.exists():
        rows = json.loads(blinded_path.read_text())
        review_key = json.loads(key_path.read_text())
        expected = {(row["case_id"], row["seed"], row["variant"])
                    for row in report["results"] if row["output"] is not None}
        actual = {(row["case_id"], row["seed"], row["variant"])
                  for row in review_key.values()}
        if (len(rows) != len(review_key) or len(review_key) != len(expected)
                or {row["review_id"] for row in rows} != set(review_key) or actual != expected):
            raise ValueError("Existing review export does not match the report; files preserved")
        return
    if blinded_path.exists() or key_path.exists():
        raise FileExistsError(
            "Incomplete review export; move the existing sidecar file before retrying"
        )
    rows, review_key = blinded_review(report)
    save(key_path, review_key)
    save(blinded_path, rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--request-profile-model", help="Keep this model's prompt profile while changing the execution model")
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--case-ids", nargs="+")
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 73, 101])
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    report = run(args)
    export_blinded_review(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
