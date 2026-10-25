"""Frozen, local-only framing/publication experiment. No app/project store writes."""

import argparse
import copy
import hashlib
import json
import shutil
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.application.ai_provider import StructuredRequest, strict_json_instructions
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig
from scripts.framing_contract import FramingAssessment, PROMPT_PATH, validate_sources

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).with_name("framing_contract.py")
REGRESSION = ROOT / "docs/evaluations/fixtures/gemma2-publication-gate-cases-2026-10-25.json"
NEW_CASES = ROOT / "docs/evaluations/fixtures/framing-v1-new-cases-2026-10-25.json"
MODEL = "gemma2:9b-instruct-q4_K_M"
MODEL_DIGEST = "c20bec88025f3aefa420efd64dca0ee4abc8e36078d6b74b0f660cdcbd5d1982"
CONFIG = OllamaProviderConfig(MODEL, temperature=0.3, timeout_seconds=180, context_length=16384)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def protected_hashes():
    paths = [ROOT / name for name in (
        "backend/app", "frontend/app", "domains/short-film", "backend/.env",
        "backend/.data", "docs/plans", "docs/roadmap.md",
    )]
    return {
        str(path.relative_to(ROOT)): file_hash(path)
        for base in paths
        for path in ([base] if base.is_file() else sorted(base.rglob("*")))
        if path.is_file() and "__pycache__" not in path.parts
    }


def snapshot(case, rules):
    return {**case["input"], "publication_rules": rules}


def request(case, prompt):
    # Expected labels, case names and split never enter the model payload.
    return StructuredRequest(prompt, json.dumps(case["input"], ensure_ascii=False),
                             FramingAssessment, "offline-framing-v1")


def decide(output, expected_snapshot, current):
    flags = {"can_save": True, "can_edit": True}
    if digest(current) != expected_snapshot:
        return {**flags, "action": "review_required", "can_publish": False,
                "reason": "stale_snapshot"}
    try:
        parsed = FramingAssessment.model_validate(output)
        cards = {card["id"]: card["text"] for card in current["cards"]}
        if len(cards) != len(current["cards"]):
            raise ValueError("Duplicate source card IDs")
        validate_sources(parsed, cards)
    except ValueError as error:
        return {**flags, "action": "review_required", "can_publish": False,
                "reason": "invalid_assessment", "error": str(error)}
    blocked = [item.topic_id for item in parsed.themes if item.stance == "endorsing"]
    uncertain = [item.topic_id for item in parsed.themes if item.stance == "unclear"]
    if parsed.language.status == "clear_violation":
        blocked.append("R4")
    elif parsed.language.status == "uncertain":
        uncertain.append("R4")
    action = "block" if blocked else "warn" if uncertain else "allow"
    return {**flags, "action": action, "can_publish": not blocked,
            "reason": "clear_violation" if blocked else "needs_context" if uncertain
            else "no_violation", "blocked_rules": blocked, "uncertain_rules": uncertain}


def warning(gate):
    if gate["action"] == "review_required":
        return "Cần kiểm tra lại bản hiện tại trước khi xuất bản; vẫn có thể lưu và sửa."
    if gate["action"] == "block":
        return "Chặn xuất bản theo quy tắc thử nghiệm: " + ", ".join(gate["blocked_rules"])
    if gate["action"] == "warn":
        return "Cần làm rõ ngữ cảnh cho: " + ", ".join(gate["uncertain_rules"])
    return ""


def frozen_cases():
    regression = json.loads(REGRESSION.read_text())
    new = json.loads(NEW_CASES.read_text())
    cases = []
    active = {1: ("R1", "critical"), 2: ("R1", "endorsing"), 3: ("R1", "unclear"),
              4: ("R2", "critical"), 5: ("R2", "endorsing"), 6: ("R2", "unclear"),
              7: ("R3", "critical"), 8: ("R3", "endorsing"), 9: ("R3", "unclear"),
              15: ("R1", "critical"), 17: ("R2", "endorsing")}
    for original in regression["cases"]:
        case = copy.deepcopy(original)
        case["split"] = "regression"
        case["expected_stances"] = dict.fromkeys(["R1", "R2", "R3"], "not_applicable")
        index = int(case["id"].split("-")[1])
        if index in active:
            topic, stance = active[index]
            case["expected_stances"][topic] = stance
        cases.append(case)
    cases.extend({**case, "split": "new"} for case in new["cases"])
    if len(regression["cases"]) != 18 or len(new["cases"]) != 12:
        raise ValueError("Expected 18 regression and 12 new cases")
    if len({case["id"] for case in cases}) != 30:
        raise ValueError("Case IDs must be unique")
    return {"rules": regression["rules"], "cases": cases}


def freeze(directory):
    directory.mkdir(parents=True, exist_ok=False)
    cases = frozen_cases()
    write(directory / "cases.json", cases)
    write(directory / "schema.json", FramingAssessment.model_json_schema())
    shutil.copyfile(PROMPT_PATH, directory / "prompt.md")
    shutil.copyfile(CONTRACT, directory / "contract.py")
    shutil.copyfile(__file__, directory / "runner.py")
    resources = [PROMPT_PATH, CONTRACT, Path(__file__).resolve(), REGRESSION, NEW_CASES,
                 Path(__file__).with_name("summarize_framing_gate_experiment.py")]
    write(directory / "manifest.json", {
        "frozen_at": datetime.now(UTC).isoformat(), "repeats": 2, "planned_calls": 60,
        "provider": asdict(OllamaProvider(CONFIG).metadata), "model_digest": MODEL_DIGEST,
        "resource_hashes": {str(path.relative_to(ROOT)): file_hash(path) for path in resources},
        "frozen_hashes": {name: file_hash(directory / name) for name in (
            "cases.json", "schema.json", "prompt.md", "contract.py", "runner.py")},
        "protected_hashes": protected_hashes(),
        "note": "Frozen before inference. No retries, output repair, relabeling or post-hoc ablation.",
    })


def verify_freeze(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["resource_hashes"].items():
        if file_hash(ROOT / name) != expected:
            raise ValueError(f"Frozen resource changed: {name}")
    for name, expected in manifest["frozen_hashes"].items():
        if file_hash(directory / name) != expected:
            raise ValueError(f"Frozen artifact changed: {name}")
    if json.loads((directory / "schema.json").read_text()) != FramingAssessment.model_json_schema():
        raise ValueError("Loaded schema differs from freeze")
    return manifest


def claim_run(directory):
    try:
        with (directory / "started.json").open("x") as stream:
            json.dump({"started_at": datetime.now(UTC).isoformat()}, stream)
    except FileExistsError:
        raise ValueError("This frozen run has already started; selective retry/resume is disabled")


def run(directory):
    manifest = verify_freeze(directory)
    if (directory / "started.json").exists():
        raise ValueError("This frozen run has already started; selective retry/resume is disabled")
    frozen = json.loads((directory / "cases.json").read_text())
    prompt = (directory / "prompt.md").read_text()
    provider = OllamaProvider(CONFIG)
    if asdict(provider.metadata) != manifest["provider"]:
        raise ValueError("Provider parameters differ from freeze")
    # Claim before network or result writes; concurrent starts must not overwrite a run.
    claim_run(directory)
    tags = httpx.get(CONFIG.base_url + "/api/tags", timeout=10, trust_env=False).json()
    model = next(item for item in tags["models"] if item["name"] == MODEL)
    if model["digest"] != manifest["model_digest"]:
        raise ValueError("Model digest differs from freeze")
    write(directory / "model.json", model)
    write(directory / "environment.json", httpx.get(
        CONFIG.base_url + "/api/version", timeout=10, trust_env=False).json())
    rows = []
    try:
        for repeat in range(1, manifest["repeats"] + 1):
            for case in frozen["cases"]:
                verify_freeze(directory)
                current = snapshot(case, frozen["rules"])
                captured_snapshot = digest(current)
                model_request = request(case, prompt)
                row = {"label": f'{case["id"]}-{repeat}', "case_id": case["id"],
                       "repeat": repeat, "split": case["split"], "input": current,
                       "snapshot": captured_snapshot, "request": {
                           "system": strict_json_instructions(model_request),
                           "user": model_request.input_text,
                           "schema": model_request.response_model.model_json_schema()},
                       "started_at": datetime.now(UTC).isoformat()}
                rows.append(row)
                write(directory / "calls.json", rows)
                print(json.dumps({"started": row["label"]}), flush=True)
                started = time.monotonic()
                try:
                    result = provider.request_structured(model_request)
                    row.update(output=result.output.model_dump(mode="json"),
                               raw_output=result.raw_output, model=result.model)
                except Exception as error:
                    row.update(error=type(error).__name__ + ": " + str(error),
                               cause=str(error.__cause__) if error.__cause__ else None,
                               raw_output=getattr(error, "raw_output", None))
                row["seconds"] = round(time.monotonic() - started, 2)
                row["gate"] = decide(row.get("output"), captured_snapshot, current)
                row["warning"] = warning(row["gate"])
                path = directory / (row["label"] + "-draft.json")
                write(path, current)
                if json.loads(path.read_text()) != current:
                    raise AssertionError("Saving local draft failed")
                edited = copy.deepcopy(current)
                edited["cards"][0]["text"] += " [Bản sửa thử offline]"
                write(path, edited)
                row["saved_and_edited"] = json.loads(path.read_text()) == edited
                row["gate_after_edit"] = decide(row.get("output"), captured_snapshot, edited)
                write(directory / "calls.json", rows)
                print(json.dumps({"done": row["label"], "action": row["gate"]["action"],
                                  "seconds": row["seconds"], "error": row.get("error")}), flush=True)
    finally:
        after = protected_hashes()
        write(directory / "checks.json", {
            "completed_calls": sum("gate" in row for row in rows),
            "protected_unchanged": after == manifest["protected_hashes"],
            "frozen_unchanged": verify_freeze(directory) == manifest,
        })
        write(directory / "loaded-models.json", httpx.get(
            CONFIG.base_url + "/api/ps", timeout=10, trust_env=False).json())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["freeze", "run"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    (freeze if args.mode == "freeze" else run)(args.directory)


if __name__ == "__main__":
    main()
