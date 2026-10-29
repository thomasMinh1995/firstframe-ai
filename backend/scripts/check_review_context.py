"""Run from repository root with the backend Python environment; local Ollama only."""

import sys, json, time, tempfile, os, argparse, re
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
from app.api.schemas.projects import ProjectResponse
from app.application.project_store import ProjectStore
from app.api.routes import projects, screenplay_reviews
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig
from app.main import create_app
from app.application.ai_provider import strict_json_instructions
from app.application.screenplay_review import PRESENTATION
import httpx


def evaluate_review(review, expectation):
    """Frozen-corpus gate: finding a conflict on the wrong passage is a failure."""
    notes = review["notes"]
    conflicts = [n for n in notes if n["kind"] == "intent_mismatch"]
    sources = {s["id"]: s for s in review["sources"]}

    def correct_pair(note):
        if any(e["source_id"] not in sources for e in note["evidence"]):
            return False
        target = any(
            e["quote"] == expectation["target_quote"]
            and sources[e["source_id"]]["category"] == "screenplay"
            and sources[e["source_id"]]["field"] == "text"
            and sources[e["source_id"]]["scene_id"] == review["target_scene_id"]
            for e in note["evidence"]
        )
        author = any(
            e["quote"] in expectation["author_quotes"]
            and sources[e["source_id"]]["category"] == "author_choice"
            for e in note["evidence"]
        )
        return target and author

    prose = [
        review["question"],
        *(n[k] for n in notes for k in ("observation", "impact", "suggestion")),
    ]
    controlled = True
    if review.get("prompt_version", "").startswith("screenplay-review-v8"):
        controlled = not review["question"] and all(
            (n["observation"], n["impact"]) in PRESENTATION["Vietnamese"].values()
            and n["suggestion"] == ""
            for n in notes
        )
    return {
        "matches_expected_presentation": controlled,
        "no_spurious_notes": not expectation.get("expected_no_notes", False) or not notes,
        "matches_expected_conflict": bool(conflicts) == expectation["expected_conflict"],
        "matches_expected_evidence": all(correct_pair(n) for n in conflicts)
        if expectation["expected_conflict"] and conflicts
        else not conflicts and not expectation["expected_conflict"],
        # These synthetic Vietnamese fixtures contain no CJK names or quoted material.
        "unexpected_cjk": any(re.search(r"[\u3400-\u9fff]", text) for text in prose),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Ten local Qwen reviews, one call per target excerpt, shared 60s/review, no retries; isolated storage."
    )
    parser.add_argument("--output", type=Path, required=True)
    root = parser.parse_args().output
    root.mkdir(parents=True, exist_ok=False)
    tmp = Path(tempfile.mkdtemp(prefix="firstframe-qa01-context-"))
    os.environ["DATASET_DIR"] = str(tmp / "dataset")
    original = json.loads(
        Path("docs/evaluations/phase6-qwen7b-2026-10-29/result.json").read_text()
    )["candidate"]["project"]
    store = ProjectStore(tmp / "projects.sqlite3")
    projects.get_project_store = lambda: store
    trace = []
    post = httpx.post

    class Measured(OllamaProvider):
        def request_structured(self, request):
            if sum(c["case"] == name for c in trace) >= case_call_limit:
                raise RuntimeError("Saved target-excerpt call budget exhausted")
            current = {
                "stage": request.stage,
                "case": name,
                "timeout_seconds": request.timeout_seconds,
                "response_schema": request.response_model.model_json_schema(),
                "instructions": request.instructions,
                "input": json.loads(request.input_text),
                "request_bytes": len(request.input_text.encode())
                + len(strict_json_instructions(request).encode()),
            }
            trace.append(current)
            start = time.monotonic()
            try:
                return super().request_structured(request)
            finally:
                current["elapsed_seconds"] = round(time.monotonic() - start, 3)
                (root / "calls.json").write_text(json.dumps(trace, ensure_ascii=False, indent=2))

    def capture(url, **kwargs):
        response = post(url, **kwargs)
        trace[-1]["options"] = kwargs["json"]["options"]
        trace[-1]["response"] = response.json()
        return response

    provider = Measured(
        OllamaProviderConfig("qwen2.5:7b", timeout_seconds=60, context_length=16384)
    )
    screenplay_reviews.get_review_provider = lambda: provider
    results = []
    expectations = json.loads(
        Path("docs/evaluations/qa01-qwen-review-v8-2026-10-29/expectations.json").read_text()
    )
    cases = [("original", original, None), ("contradiction", original, None)]
    frozen = json.loads(
        Path("docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json").read_text()
    )
    assert len(frozen) == 6, "Expected the frozen six-case review set"
    cases += [(c["name"], c["project"], c["request"]["target_scene_id"]) for c in frozen]
    additional = json.loads(
        Path("docs/evaluations/qa01-qwen-review-v8-2026-10-29/additional-inputs.json").read_text()
    )
    cases += [(c["name"], c["project"], c["target_scene_id"]) for c in additional]
    with (
        TestClient(create_app()) as client,
        patch("app.infrastructure.ollama_provider.httpx.post", capture),
    ):
        for name, source, target_id in cases:
            p = ProjectResponse.model_validate(source).model_copy(deep=True)
            p.id = str(uuid4())
            p.screenplay_reviews = []
            if name == "contradiction":
                p.screenplay.scenes[0].blocks[0].text = "Cô mở lá thư và đọc lời xin lỗi của cha."
            selected_scene = next(
                s for s in p.screenplay.scenes if s.id == (target_id or p.screenplay.scenes[0].id)
            )
            case_call_limit = sum(
                (len(b.text) + 999) // 1000 for b in selected_scene.blocks if b.text.strip()
            )
            store.create(p.model_dump(mode="json", exclude_computed_fields=True))
            response = client.post(
                f"/api/projects/{p.id}/screenplay-reviews",
                json={
                    "revision": p.revision,
                    "request_id": str(uuid4()),
                    "target_scene_id": target_id or p.screenplay.scenes[0].id,
                },
            )
            saved = client.get(f"/api/projects/{p.id}").json()
            review = saved["screenplay_reviews"][-1]
            item = {
                "case": name,
                "expected_conflict": name == "contradiction" or name.endswith("-violating"),
                "status": response.status_code,
                "review": review,
                "unchanged_screenplay": saved["screenplay"] == p.screenplay.model_dump(mode="json"),
                "detected_conflict": any(n["kind"] == "intent_mismatch" for n in review["notes"]),
            }
            item.update(evaluate_review(review, expectations[name]))
            if response.status_code != 200:
                item["error_response"] = response.text
            results.append(item)
            (root / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
            print(
                json.dumps({k: v for k, v in item.items() if k != "review"}, ensure_ascii=False),
                flush=True,
            )
    (root / "summary.json").write_text(
        json.dumps(
            {
                "calls": len(trace),
                "http_200": sum(r["status"] == 200 for r in results),
                "all_screenplays_unchanged": all(r["unchanged_screenplay"] for r in results),
                "context_rejections": sum(
                    r["review"]["error"] == "ScreenplayContextTooLarge" for r in results
                ),
                "false_positives": sum(
                    r["detected_conflict"] and not r["expected_conflict"] for r in results
                ),
                "missed_conflicts": sum(
                    r["expected_conflict"] and not r["detected_conflict"] for r in results
                ),
                "bad_evidence_pairs": sum(not r["matches_expected_evidence"] for r in results),
                "unexpected_cjk": sum(r["unexpected_cjk"] for r in results),
                "bad_presentations": sum(not r["matches_expected_presentation"] for r in results),
                "spurious_notes": sum(not r["no_spurious_notes"] for r in results),
                "release_acceptance": "pending independent reading and model reliability",
            },
            indent=2,
        )
    )
    print("Evidence", root, flush=True)
    if any(
        r["status"] != 200
        or not r["unchanged_screenplay"]
        or not r["matches_expected_conflict"]
        or not r["matches_expected_evidence"]
        or r["unexpected_cjk"]
        for r in results
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
