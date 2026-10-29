"""Run from repository root with the backend Python environment; local Ollama only."""

import sys, json, time, tempfile, os, argparse
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
import httpx

parser = argparse.ArgumentParser(
    description="Eight synthetic local Qwen reviews, no retries; separate SQLite and dataset."
)
parser.add_argument("--output", type=Path, required=True)
root = parser.parse_args().output
root.mkdir(parents=True, exist_ok=False)
tmp = Path(tempfile.mkdtemp(prefix="firstframe-qa01-context-"))
os.environ["DATASET_DIR"] = str(tmp / "dataset")
original = json.loads(Path("docs/evaluations/phase6-qwen7b-2026-10-29/result.json").read_text())[
    "candidate"
]["project"]
store = ProjectStore(tmp / "projects.sqlite3")
projects.get_project_store = lambda: store
trace = []
post = httpx.post


class Measured(OllamaProvider):
    def request_structured(self, request):
        if len(trace) >= 8:
            raise RuntimeError("Frozen eight-call budget exhausted")
        current = {
            "stage": request.stage,
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


provider = Measured(OllamaProviderConfig("qwen2.5:7b", timeout_seconds=60, context_length=16384))
screenplay_reviews.get_review_provider = lambda: provider
results = []
cases = [("original", original, None), ("contradiction", original, None)]
frozen = json.loads(
    Path("docs/evaluations/m3-scene-review-qwen7b-2026-10-27/inputs.json").read_text()
)
assert len(frozen) == 6, "Expected the frozen six-case review set"
cases += [(c["name"], c["project"], c["request"]["target_scene_id"]) for c in frozen]
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
            "status": response.status_code,
            "review": review,
            "unchanged_screenplay": saved["screenplay"] == p.screenplay.model_dump(mode="json"),
            "detected_conflict": any(n["kind"] == "intent_mismatch" for n in review["notes"]),
        }
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
            "release_acceptance": "pending independent reading and model reliability",
        },
        indent=2,
    )
)
print("Evidence", root, flush=True)
if any(r["status"] != 200 for r in results):
    raise SystemExit(1)
