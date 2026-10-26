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
from app.application import workflow
from app.api.schemas.scenes import SceneSuggestionResult
from app.application.ai_provider import ProviderTimeoutError, StructuredResult
from app.application.project_store import ProjectStore
from app.main import create_app


class WorkspaceProvider(FakeProvider):
    fail_critic = False
    plans = 0
    fail_scenes = False

    def request_structured(self, request):
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
    return {**state, "provider_stages": [r.stage for r in provider.requests]}


@app.post("/__test/control")
async def control(values: dict):
    assert set(values) <= {"fail_critic", "hold_suffix", "lose_response_suffix", "release", "fail_scenes"}
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
