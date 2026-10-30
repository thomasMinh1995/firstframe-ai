"""Disposable API with real draft checkpoints and gated fake providers for DR-05/06.

Run with backend's Python environment. All data lives in a new temporary folder.
POST /__test/control accepts release, auto, fail_run, fail_candidate, ask, fail_stage, lose_adopt.
"""
import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
directory = Path(tempfile.mkdtemp(prefix="firstframe-workspace-transitions-"))
os.environ["DATASET_DIR"] = str(directory / "datasets")
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware
from app.api.routes import projects, draft_runs
from app.application.project_store import ProjectStore
from app.application import draft_workflow
from app.application.ai_provider import StructuredResult, ProviderTimeoutError
from app.main import create_app
from test_projects import start_project
from test_generate_workflow import FakeProvider
from test_scene_suggestions import SceneProvider
from test_screenplay_writing import WritingProvider
from test_screenplay_review import ReviewProvider

state = {"stage": None, "calls": [], "auto": False, "fail_run": False, "fail_candidate": False, "ask": False, "fail_stage": None, "lose_adopt": False}
release = threading.Event()
class Gated:
    def __init__(self, provider):
        self.provider, self.metadata = provider, provider.metadata
    def request_structured(self, request):
        state["stage"] = request.stage
        state["calls"].append(request.stage)
        if not state["auto"]:
            if not release.wait(180):
                raise TimeoutError("Fixture gate timeout")
            release.clear()
        if request.stage == state["fail_stage"]:
            raise ProviderTimeoutError("Fixture: unknown provider result")
        result = self.provider.request_structured(request)
        if result.output.__class__.__name__ == "_ReasoningOutput" and not state["ask"]:
            result = StructuredResult(output=result.output.model_copy(update={"missing_information": []}), model=result.model)
        return result

providers = [Gated(p) for p in (FakeProvider(), SceneProvider(), WritingProvider(), ReviewProvider())]
projects.get_project_store = lambda: ProjectStore(directory / "projects.sqlite3")
draft_runs.providers = lambda: providers
app = create_app()
@app.middleware("http")
async def connection(request: Request, call_next):
    if request.method == "GET" and "/draft-runs/" in request.url.path:
        candidate = request.url.path.endswith("/candidate")
        if state["fail_candidate" if candidate else "fail_run"]:
            return JSONResponse({"detail": "Fixture: mất kết nối tạm thời"}, status_code=503)
    response = await call_next(request)
    if request.method == "POST" and request.url.path.endswith("/adopt") and state["lose_adopt"]:
        state["lose_adopt"] = False
        return JSONResponse({"detail": "Fixture: phản hồi nhận bản bị mất"}, status_code=503)
    return response
@app.get("/__test/state")
def inspect():
    return state
@app.post("/__test/control")
def control(values: dict):
    assert set(values) <= {"release", "auto", "fail_run", "fail_candidate", "ask", "fail_stage", "lose_adopt"}
    for key in ("auto", "fail_run", "fail_candidate", "ask", "lose_adopt"):
        if key in values: state[key] = bool(values[key])
    if values.get("release") or state["auto"]: release.set()
    if "fail_stage" in values: state["fail_stage"] = values["fail_stage"]
    return state
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3034"], allow_methods=["*"], allow_headers=["*"])
with TestClient(app) as client:
    project = start_project(client)
    run_id = str(uuid4())
    # Seed a durable run without launching a worker before the server is available.
    original_launch = draft_workflow.launch
    draft_workflow.launch = lambda *args: None
    response = client.post(f"/api/projects/{project['id']}/draft-runs", json={"revision": project["revision"], "request_id": run_id})
    assert response.status_code == 200, response.text
    draft_workflow.launch = original_launch
seed = {"directory": str(directory), "project_id": project["id"], "run_id": run_id}
(directory / "seed.json").write_text(json.dumps(seed), encoding="utf-8")
@app.post("/__test/start")
def start():
    assert not state["calls"]
    draft_workflow.launch(draft_runs.store(), project["id"], run_id, providers)
    return seed
print(json.dumps(seed), flush=True)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8034)
