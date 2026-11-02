"""SI-03-only HTTP fixture: fake providers, fresh stores, no outbound HTTP."""
import asyncio
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import threading
import time

backend = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(backend), str(backend / "tests")]
data = Path(tempfile.mkdtemp(prefix="firstframe-si03-"))
os.environ["DATASET_DIR"] = str(data / "datasets")

import httpx
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from app.main import create_app
from app.api.routes import draft_runs, projects, scene_sketches, screenplays, screenplay_reviews
from app.application import workflow
from app.application.ai_provider import MalformedProviderResponseError, ProviderTimeoutError
from app.application.project_store import ProjectStore
from test_generate_workflow import FakeProvider
from test_plan_recovery import ready
from test_projects import start_project
from test_scene_suggestions import SceneProvider
from test_screenplay_writing import WritingProvider
from test_screenplay_review import ReviewProvider


def no_network(*args, **kwargs):
    raise AssertionError("SI-03 fixture forbids outbound HTTP and real providers")


httpx.HTTPTransport.handle_request = no_network
scene_sketches.get_image_provider = no_network
projects.get_project_store = lambda: ProjectStore(data / "projects.sqlite3")
app = create_app()
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3055"], allow_methods=["*"], allow_headers=["*"])
cases = {}
active = None


class Provider:
    def __init__(self, case, delegate, kind):
        self.case, self.delegate, self.kind = case, delegate, kind
        self.metadata = delegate.metadata

    def request_structured(self, request):
        c = self.case
        if not c.armed:
            return self.delegate.request_structured(request)
        key = hashlib.sha256((request.stage + request.input_text + request.instructions).encode()).hexdigest()
        index = sum(row["kind"] == self.kind for row in c.calls)
        c.calls.append({"kind": self.kind, "stage": request.stage, "key": key})
        gate = "critic" if self.kind == "text" and request.stage == "evaluation" else (
            "outline" if self.kind == "outline" else f"scene:{index}" if self.kind == "writer" else "review" if self.kind == "reviewer" else None)
        if request.stage == "planning" and c.fault.startswith("planner_"):
            error = MalformedProviderResponseError if c.fault == "planner_json" else ProviderTimeoutError
            raise error("fake planner failure")
        if gate and (c.mode == "draft" or gate == "critic"):
            c.waiting = gate
            c.events.append({"kind": "waiting", "gate": gate, "ms": c.ms()})
            if not c.gates.setdefault(gate, threading.Event()).wait(90):
                raise ProviderTimeoutError("fixture gate deadline")
            c.waiting = None
            if gate == "critic" and c.fault.startswith("critic_"):
                error = MalformedProviderResponseError if c.fault == "critic_json" else ProviderTimeoutError
                raise error("fake critic failure")
            if gate == "scene:1" and c.fault == "scene_unknown":
                raise ProviderTimeoutError("fake unknown second scene outcome")
        result = self.delegate.request_structured(request)
        if request.stage == "reasoning" and c.mode == "draft":
            result.output.missing_information = []
        if request.stage == "planning":
            result.output.story_plan.working_title.title = "Story plan SI-03"
        return result


class Case:
    def __init__(self, body):
        self.mode = body.get("mode", "plan")
        self.fault = body.get("fault", "")
        self.transport = body.get("transport", "normal")
        self.armed = False
        self.calls, self.events, self.gates = [], [], {}
        self.waiting = None
        self.started = time.perf_counter()
        scenes = SceneProvider()
        scenes.count = body.get("scenes", 2)
        self.providers = [Provider(self, p, kind) for p, kind in zip(
            [FakeProvider(), scenes, WritingProvider(), ReviewProvider()], ["text", "outline", "writer", "reviewer"])]

    def ms(self):
        return round((time.perf_counter() - self.started) * 1000, 3)


workflow.create_provider = lambda: active.providers[0]
projects.create_provider = lambda: active.providers[0]
projects.get_scene_provider = lambda: active.providers[1]
screenplays.get_screenplay_provider = lambda: active.providers[2]
screenplay_reviews.get_review_provider = lambda: active.providers[3]
draft_runs.providers = lambda: active.providers
save_project = projects.save_project


def save_with_trace(project, stage="saving"):
    result = save_project(project, stage)
    c = cases.get(project.id)
    if c:
        c.events.append({"kind": stage, "revision": result.revision, "ms": c.ms()})
    return result


projects.save_project = save_with_trace


@app.post("/_fixture/new")
async def new_case(request: Request):
    global active
    body = await request.json()
    active = c = Case(body)
    client = TestClient(app)
    p = start_project(client) if c.mode == "draft" else ready(client, body.get("existing", True))
    c.project_id, c.original = p["id"], p
    cases[p["id"]] = c
    c.armed = True
    return {"fixture": True, "project": p}


@app.get("/_fixture/{project_id}")
def state(project_id: str):
    c = cases[project_id]
    runs = draft_runs.store().rows(project_id)
    return {"fixture": True, "waiting": c.waiting, "calls": c.calls, "events": c.events,
            "original": c.original, "project": projects.load_project(project_id).model_dump(mode="json"),
            "run": draft_runs.brief(runs[0]) if runs else None,
            "candidate": draft_runs.candidate_response(runs[0]) if runs else None}


@app.post("/_fixture/{project_id}/release")
async def release(project_id: str, request: Request):
    c = cases[project_id]
    body = await request.json()
    gates = list(c.gates) if body.get("all") else [body["gate"]]
    for gate in gates:
        c.gates.setdefault(gate, threading.Event()).set()
    if body.get("all"):
        for gate in ["critic", "outline", "review", *(f"scene:{i}" for i in range(6))]:
            c.gates.setdefault(gate, threading.Event()).set()
    return {"fixture": True}


class TransportFixture:
    """Cut only the client stream after its checkpoint, or inject fixture heartbeats."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        c = next((c for pid, c in cases.items() if path == f"/api/projects/{pid}/plan/stream"), None)
        if not c:
            return await self.app(scope, receive, send)
        ended, ticker = False, None

        async def heartbeat():
            while True:
                await asyncio.sleep(0.1)
                if ended:
                    return
                await send({"type": "http.response.body", "body": b"\n", "more_body": True})

        async def forward(message):
            nonlocal ended, ticker
            if ended:
                return
            if message["type"] == "http.response.start" and c.transport == "heartbeat":
                await send(message)
                ticker = asyncio.create_task(heartbeat())
                return
            if message["type"] == "http.response.body":
                body = message.get("body", b"")
                if c.transport == "truncate" and b'"type": "checkpoint"' in body:
                    ended = True
                    c.events.append({"kind": "transport_eof", "ms": c.ms()})
                    await send({**message, "more_body": False})
                    return
                if not message.get("more_body", False):
                    ended = True
                    if ticker:
                        ticker.cancel()
            await send(message)

        try:
            await self.app(scope, receive, forward)
        finally:
            if ticker:
                ticker.cancel()


application = TransportFixture(app)
if __name__ == "__main__":
    import uvicorn
    print(f"SI03_FIXTURE_DATA={data}", flush=True)
    uvicorn.run(application, host="127.0.0.1", port=8055, log_level="warning")
