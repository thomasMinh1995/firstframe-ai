"""Disposable localhost API for UI checks; never opens the application's project DB.

Run from backend: .venv/bin/python tests/ui_workspace_fixture.py
Point an isolated frontend build at http://127.0.0.1:8034.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
directory = Path(tempfile.mkdtemp(prefix="firstframe-workspace-"))
os.environ["DATASET_DIR"] = str(directory / "datasets")

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware
from test_generate_workflow import FakeProvider
from test_projects import develop_project, start_project

from app.api.routes import projects as routes
from app.api.routes import screenplay_reviews
from test_screenplay_review import ReviewProvider
from app.api.routes import screenplays
from test_screenplay_writing import WritingProvider
from app.api.routes import scene_sketches
from test_scene_sketches import FakeImageProvider
from app.application import workflow
from app.api.schemas.scenes import SceneSuggestionResult, StagingResult
from app.application.ai_provider import ProviderTimeoutError, StructuredResult
from app.application.project_store import ProjectStore
from app.main import create_app


class WorkspaceProvider(FakeProvider):
    fail_critic = False
    plans = 0
    fail_scenes = False
    bad_staging = False
    empty_staging = False

    def request_structured(self, request):
        if request.stage == "staging_generation":
            self.requests.append(request)
            data = json.loads(request.input_text)
            anchor = next(s for s in data["sources"] if s["id"] == f"scene:{data['target_scene_id']}:action")
            ideas = [{"field": key, "evidence": [{"source_id": anchor["id"], "quote": "Quote không có nguồn" if self.bad_staging else anchor["text"][:80]}],
                      "reason": "Khoảng cách quanh lá thư giữ quyền lựa chọn.", "suggestion": text,
                      "purpose": "Để người xem cảm nhận khoảng lặng."} for key, text in (
                          ("blocking", "Cha lùi một bước, giữ lối đi trống."), ("setting", "Giữ mặt bàn trống quanh lá thư."),
                          ("composition", "Để lá thư giữa hai nhân vật trong cùng khung."))]
            return StructuredResult(output=StagingResult(ideas=[] if self.empty_staging else ideas,
                question="Bạn muốn giữ khoảng cách giữa hai người thế nào?" if self.empty_staging else ""), model="fixture-staging")
        if request.stage == "scene_generation":
            self.requests.append(request)
            if self.fail_scenes:
                raise ProviderTimeoutError("UI fixture scene failure")
            mode = json.loads(request.input_text)["mode"]
            return StructuredResult(output=SceneSuggestionResult(scenes=[{
                "title": f"Cảnh đề xuất {i + 1}", "action": "Cha đặt thư. Con nhìn rồi dừng lại.",
                "purpose": "Giữ khoảng lặng.", "transition": "Cắt trước câu trả lời.",
            } for i in range(2 if mode == "list" else 1)]), model="fixture-scenes")
        if self.fail_critic and request.stage == "evaluation":
            self.requests.append(request)
            raise ProviderTimeoutError("UI fixture critic failure")
        result = super().request_structured(request)
        if request.stage == "planning":
            self.plans += 1
            result.output.story_plan.working_title.title = f"Đề xuất {self.plans}"
            result.output.story_plan.logline.text = f"Nội dung đề xuất {self.plans}: người cha học cách lắng nghe."
        return result


provider = WorkspaceProvider()
review_provider = ReviewProvider()
screenplay_reviews.get_review_provider = lambda: review_provider
writing_provider = WritingProvider()
screenplays.get_screenplay_provider = lambda: writing_provider
image_provider = FakeImageProvider()
scene_sketches.get_image_provider = lambda: image_provider
routes.get_project_store = lambda: ProjectStore(directory / "projects.sqlite3")
workflow.create_provider = lambda: provider
app = create_app()
state = {"calls": [], "hold_suffix": None, "held": False, "lose_response_suffix": None}
release = asyncio.Event()


@app.middleware("http")
async def record(request: Request, call_next):
    if not request.url.path.startswith("/api/projects"):
        return await call_next(request)
    body = await request.body()
    call = {"method": request.method, "path": request.url.path,
            "body": json.loads(body) if body else None}
    state["calls"].append(call)
    if request.method in {"PUT", "POST"} and state["hold_suffix"] and request.url.path.endswith(state["hold_suffix"]):
        state["hold_suffix"] = None
        state["held"] = True
        release.clear()
        await asyncio.wait_for(release.wait(), timeout=120)
        state["held"] = False
    response = await call_next(request)
    call["status"] = response.status_code
    if request.method in {"PUT", "POST"} and state["lose_response_suffix"] and request.url.path.endswith(state["lose_response_suffix"]):
        state["lose_response_suffix"] = None
        return JSONResponse({"detail": "Fixture: kết quả đã xử lý nhưng phản hồi bị mất. Hãy mở lại bản đã lưu."}, status_code=503)
    return response


@app.get("/__test/state")
def inspect():
    return {**state, "provider_stages": [r.stage for r in provider.requests], "image_requests": len(image_provider.requests), "writing_requests": len(writing_provider.requests), "review_requests": len(review_provider.requests)}


@app.post("/__test/control")
async def control(values: dict):
    assert set(values) <= {"fail_critic", "hold_suffix", "lose_response_suffix", "release", "fail_scenes", "bad_staging", "empty_staging", "fail_sketch", "fail_writing", "fail_review", "bad_review", "empty_review"}
    if "fail_review" in values:
        review_provider.error = ProviderTimeoutError("fixture review timeout") if values["fail_review"] else None
    if "bad_review" in values:
        review_provider.mode = "bad_quote" if values["bad_review"] else "valid"
    if "empty_review" in values:
        review_provider.mode = "empty" if values["empty_review"] else "valid"
    if "fail_writing" in values:
        writing_provider.error = ProviderTimeoutError("fixture writing timeout") if values["fail_writing"] else None
    if "fail_sketch" in values:
        image_provider.error = ProviderTimeoutError("fixture image timeout") if values["fail_sketch"] else None
    for key in ("bad_staging", "empty_staging"):
        if key in values:
            setattr(provider, key, values[key])
    if "fail_scenes" in values:
        provider.fail_scenes = values["fail_scenes"]
    if "fail_critic" in values:
        provider.fail_critic = values["fail_critic"]
    for key in ("hold_suffix", "lose_response_suffix"):
        if key in values:
            state[key] = values[key]
    if values.get("release"):
        release.set()
    return {"ok": True}


routes.get_scene_provider = lambda: provider
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3034"],
                   allow_methods=["*"], allow_headers=["*"])
with TestClient(app) as client:
    project = develop_project(client, start_project(client))
    assert project["draft"]["title"] == "Đề xuất 1"
    assert project["feedback_is_current"]
state["calls"].clear()
provider.requests.clear()
(directory / "seed.json").write_text(json.dumps(project, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"directory": str(directory), "project_id": project["id"]}), flush=True)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8034)
