import asyncio
import json
import threading

import pytest
from test_plan_recovery import ready
from test_projects import project_client, payload  # noqa: F401

from app.api.routes import projects as routes
from app.api.schemas.projects import RevisionRequest
from app.application.ai_provider import ProviderTimeoutError


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("opt_in", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_content_checkpoint_is_opt_in_and_preserves_saved_generation(project_client, monkeypatch, existing, opt_in, failed):
    client, provider = project_client
    before = ready(client, existing)
    original = provider.request_structured
    calls = []

    def respond(request):
        calls.append(request.stage)
        if failed and request.stage == "evaluation":
            raise ProviderTimeoutError("private diagnostic")
        return original(request)

    monkeypatch.setattr(provider, "request_structured", respond)
    url = f"/api/projects/{before['id']}"
    response = client.post(url + "/plan/stream" + ("?checkpoints=true" if opt_in else ""), json={"revision": before["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    checkpoints = [e for e in events if e["type"] == "checkpoint"]
    assert len(checkpoints) == int(opt_in)
    assert calls == ["planning", "evaluation"]
    assert events[-1]["type"] == "result"
    final = events[-1]["project"]
    assert final["revision"] == before["revision"] + 2
    assert client.get(url).json() == final
    if opt_in:
        event = checkpoints[0]
        saved = event["project"]
        generation = saved["plan_generations"][-1]
        assert event["generation_id"] == generation["id"]
        assert event["stage"] == "plan_checkpoint"
        assert saved["revision"] == before["revision"] + 1
        assert generation["source_revision"] == before["revision"]
        assert generation["critic_status"] == "pending" and generation["feedback"] is None
        assert final["plan_generations"][-1]["critic_status"] == ("failed" if failed else "reviewed")
        assert events.index(event) < next(i for i, e in enumerate(events) if e.get("stage") == "evaluation")
        if existing:
            assert saved["draft"] == before["draft"] and saved["feedback_source"] == before["feedback_source"]
            assert generation["applied_revision"] is None
        else:
            assert saved["draft"] == generation["draft"] and saved["feedback"] is None


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("disconnect", [False, True])
def test_checkpoint_arrives_while_critic_is_blocked_and_survives_disconnect(project_client, monkeypatch, existing, disconnect):
    client, provider = project_client
    before = ready(client, existing)
    release, entered = threading.Event(), threading.Event()
    original = provider.request_structured
    calls = []

    def delayed(request):
        calls.append(request.stage)
        if request.stage == "evaluation":
            entered.set()
            assert release.wait(5)
        return original(request)

    monkeypatch.setattr(provider, "request_structured", delayed)

    async def read():
        response = await routes.stream_project_operation(before["id"], "plan", RevisionRequest(revision=before["revision"]), checkpoints=True)
        iterator = response.body_iterator
        try:
            while True:
                event = json.loads(await asyncio.wait_for(anext(iterator), 2))
                if event["type"] == "checkpoint":
                    break
            assert await asyncio.to_thread(entered.wait, 2)
            saved = client.get(f"/api/projects/{before['id']}").json()
            assert saved == event["project"]
            assert saved["plan_generations"][-1]["critic_status"] == "pending"
            release.set()
            if not disconnect:
                remaining = [json.loads(line) async for line in iterator]
                assert remaining[-1]["type"] == "result"
        finally:
            release.set()
            await asyncio.wait_for(iterator.aclose(), 3)

    asyncio.run(read())
    final = client.get(f"/api/projects/{before['id']}").json()
    assert final["plan_generations"][-1]["critic_status"] == "reviewed"
    assert calls == ["planning", "evaluation"]


@pytest.mark.parametrize("conflict", [False, True])
def test_no_checkpoint_when_planner_or_save_fails(project_client, monkeypatch, conflict):
    client, provider = project_client
    before = ready(client)
    original = provider.request_structured
    url = f"/api/projects/{before['id']}"

    def fail(request):
        if conflict:
            changed = payload(before)
            changed["idea"] += " Author's newer idea."
            assert client.put(url, json=changed).status_code == 200
            return original(request)
        raise ProviderTimeoutError("offline")

    monkeypatch.setattr(provider, "request_structured", fail)
    response = client.post(url + "/plan/stream?checkpoints=true", json={"revision": before["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert not any(e["type"] == "checkpoint" for e in events)
    assert events[-1]["type"] == "error"
    assert not client.get(url).json()["plan_generations"]
