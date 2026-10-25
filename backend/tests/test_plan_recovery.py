import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient
from test_projects import develop_project, payload, project_client, start_project

from app.api.routes import projects as routes
from app.api.schemas.projects import RevisionRequest
from app.application.ai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from app.application.dataset import DatasetStore
from app.application.demo import _project_pair, _read_recordings
from app.main import create_app


def ready(client, existing=False):
    project = start_project(client)
    if existing:
        return develop_project(client, project)
    url = f"/api/projects/{project['id']}"
    project = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    data = payload(project)
    data["answers"] = ["Tomorrow", "An apology; keep the ending open"]
    return client.put(url, json=data).json()


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("failure", [ProviderTimeoutError, ProviderRequestError,
                                     MalformedProviderResponseError, MissingProviderConfigurationError])
def test_critic_failure_keeps_a_durable_plan_before_critic_and_needs_no_replan(
    project_client, monkeypatch, local_dataset_directory, existing, stream, failure,
):
    client, provider = project_client
    before = ready(client, existing)
    url = f"/api/projects/{before['id']}"
    original = provider.request_structured
    calls = []
    failing = True

    def respond(request):
        calls.append(request.stage)
        if request.stage == "evaluation":
            checkpoint = TestClient(create_app()).get(url).json()
            if failing:
                generation = checkpoint["plan_generations"][-1]
                assert generation["critic_status"] == "pending"
                assert generation["source_revision"] == before["revision"]
                assert generation["context"] == before["author_context"]
                assert json.loads(generation["source_content"])["draft"] == before["draft"]
                if existing:
                    assert checkpoint["draft"] == before["draft"]
                    assert checkpoint["feedback_source"] == before["feedback_source"]
                else:
                    assert checkpoint["draft"] == generation["draft"]
                    assert checkpoint["feedback"] is None
                raise failure("private provider diagnostic")
        result = original(request)
        if request.stage == "planning":
            result.output.story_plan.working_title.title = "Recovered plan"
        return result

    monkeypatch.setattr(provider, "request_structured", respond)
    response = client.post(f"{url}/plan{'/stream' if stream else ''}", json={"revision": before["revision"]})
    assert response.status_code == 200
    if stream:
        events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
        assert events[-1]["type"] == "result"
        assert {"type": "progress", "stage": "evaluation", "status": "failed"} in events
        saved = events[-1]["project"]
    else:
        saved = response.json()
    assert "private provider diagnostic" not in response.text
    assert saved["revision"] == before["revision"] + 2
    generation = saved["plan_generations"][-1]
    assert generation["critic_status"] == "failed"
    assert generation["feedback"] is generation["feedback_source"] is None
    assert generation["draft"]["title"] == "Recovered plan"
    assert generation["applied_revision"] == (None if existing else before["revision"] + 1)
    assert TestClient(create_app()).get(url).json() == saved
    # No reading of raw dataset recordings is required to reopen or accept a plan.
    assert client.get(url).json() == saved
    record = DatasetStore(local_dataset_directory).records()[-1]
    assert record["status"] == "failed" and record["workflow_complete"] is False
    assert record["run_id"] not in _read_recordings([record])
    if existing:
        assert saved["draft"] == before["draft"]
        assert saved["feedback"] == before["feedback"]
        assert saved["feedback_source"] == before["feedback_source"]
        assert saved["versions"] == before["versions"]
        response = client.post(f"{url}/plans/{generation['id']}/accept", json={"revision": saved["revision"]})
        assert response.status_code == 200
        saved = response.json()
        assert saved["draft"] == generation["draft"]
        assert saved["feedback"] is saved["feedback_source"] is None
        assert not saved["feedback_is_current"]
        assert any(v["draft"] == before["draft"] and v["feedback_source"] == before["feedback_source"]
                   for v in saved["versions"])
    # Review uses the recovered/manual draft, without another planning request.
    edited = payload(saved)
    edited["draft"]["logline"] = "Author's manual revision after critic failure."
    saved = client.put(url, json=edited).json()
    failing = False
    reviewed = client.post(f"{url}/review", json={"revision": saved["revision"]}).json()
    assert reviewed["draft"] == edited["draft"]
    assert reviewed["feedback_is_current"]
    assert reviewed["feedback_source"]["draft"] == edited["draft"]
    assert calls.count("planning") == 1, "critic failure recovery must not need another plan"
    assert calls.count("evaluation") == 2
    assert TestClient(create_app()).get(url).json() == reviewed


def test_successful_regeneration_is_a_separate_proposal_with_exact_feedback_source(
    project_client, monkeypatch, local_dataset_directory,
):
    client, provider = project_client
    before = ready(client, existing=True)
    url = f"/api/projects/{before['id']}"
    original = provider.request_structured

    def different_plan(request):
        result = original(request)
        if request.stage == "planning":
            result.output.story_plan.working_title.title = "Separate proposal"
        return result

    monkeypatch.setattr(provider, "request_structured", different_plan)
    proposed = client.post(f"{url}/plan", json={"revision": before["revision"]}).json()
    generation = proposed["plan_generations"][-1]
    assert generation["critic_status"] == "reviewed"
    assert generation["applied_revision"] is None
    assert generation["id"] in proposed["applicable_plan_ids"]
    for field in ("draft", "feedback", "feedback_source", "versions"):
        assert proposed[field] == before[field]
    assert generation["feedback_source"]["draft"] == generation["draft"]
    assert generation["feedback_source"]["context"] == before["author_context"]
    assert generation["feedback_source"]["artifact_id"] == generation["feedback"]["artifact_id"]
    assert "Separate proposal" in provider.requests[-1].input_text
    record = DatasetStore(local_dataset_directory).records()[-1]
    assert record["status"] == "completed" and record["workflow_complete"] is False
    assert record["output"]["draft"] == before["draft"], "record the actual working draft"
    assert record["output"]["plan_generation"]["draft"] == generation["draft"]
    with pytest.raises(ValueError, match="unaccepted proposal"):
        _project_pair(_read_recordings([record])[record["run_id"]])
    requests = len(provider.requests)
    accept_url = f"{url}/plans/{generation['id']}/accept"
    response = client.post(accept_url, json={"revision": proposed["revision"]})
    assert response.status_code == 200
    accepted = response.json()
    assert accepted["draft"] == generation["draft"]
    assert accepted["feedback"] == generation["feedback"]
    assert accepted["feedback_source"] == generation["feedback_source"]
    assert accepted["feedback_is_current"]
    assert generation["id"] not in accepted["applicable_plan_ids"]
    assert any(v["draft"] == before["draft"] for v in accepted["versions"])
    # Both retrying the lost response and submitting again with a refreshed revision are safe.
    for revision in [proposed["revision"], accepted["revision"]]:
        assert client.post(accept_url, json={"revision": revision}).status_code == 409
        assert client.get(url).json() == accepted
    assert len(provider.requests) == requests, "acceptance and retries never invoke AI"
    foreign = ready(client)
    assert client.post(f"/api/projects/{foreign['id']}/plans/{generation['id']}/accept",
                       json={"revision": foreign["revision"]}).status_code == 404


@pytest.mark.parametrize("field", ["draft", "idea", "constraints", "answers", "response_language"])
def test_changed_source_cannot_be_bypassed_by_reloading_the_revision(project_client, field):
    client, _ = project_client
    before = ready(client, existing=True)
    url = f"/api/projects/{before['id']}"
    proposed = client.post(f"{url}/plan", json={"revision": before["revision"]}).json()
    generation = proposed["plan_generations"][-1]
    edited = payload(proposed)
    if field == "draft":
        edited["draft"]["logline"] = "A newer manual draft."
    elif field == "response_language":
        edited[field] = "en"
    elif field == "constraints":
        edited[field] = ["Different constraint"]
    elif field == "answers":
        edited[field][0] = "Changed author choice"
    else:
        edited[field] = "Another story."
    changed = client.put(url, json=edited).json()
    assert generation["id"] not in changed["applicable_plan_ids"]
    for revision in [proposed["revision"], changed["revision"]]:
        response = client.post(f"{url}/plans/{generation['id']}/accept", json={"revision": revision})
        assert response.status_code == 409
        assert client.get(url).json() == changed


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("when", ["planning", "evaluation"])
@pytest.mark.parametrize("critic_fails", [False, True])
def test_late_planner_or_critic_never_rebases_over_a_newer_save(
    project_client, monkeypatch, existing, when, critic_fails,
):
    client, provider = project_client
    before = ready(client, existing)
    url = f"/api/projects/{before['id']}"
    original = provider.request_structured
    peer_saved = None
    calls = []

    def respond(request):
        nonlocal peer_saved
        calls.append(request.stage)
        if request.stage == when:
            latest = client.get(url).json()
            edited = payload(latest)
            if latest["draft"]:
                edited["draft"]["logline"] = "Newer manual revision from the other window."
            else:
                edited["idea"] += " Changed before planner returns."
            response = client.put(url, json=edited)
            assert response.status_code == 200
            peer_saved = response.json()
        if request.stage == "evaluation" and critic_fails:
            raise ProviderTimeoutError("late timeout")
        return original(request)

    monkeypatch.setattr(provider, "request_structured", respond)
    response = client.post(f"{url}/plan", json={"revision": before["revision"]})
    assert response.status_code == 409
    assert client.get(url).json() == peer_saved
    if when == "planning":
        assert calls == ["planning"], "no critic after a failed checkpoint"
    else:
        assert peer_saved["plan_generations"][-1]["critic_status"] == "pending"


@pytest.mark.parametrize("existing", [False, True])
def test_disconnected_plan_stream_finishes_checkpoint(
    project_client, monkeypatch, existing,
):
    client, provider = project_client
    before = ready(client, existing)
    url = f"/api/projects/{before['id']}"
    release = threading.Event()
    original = provider.request_structured

    def delayed(request):
        if request.stage == "evaluation":
            assert release.wait(timeout=5)
            raise ProviderTimeoutError("critic unavailable after disconnect")
        return original(request)

    monkeypatch.setattr(provider, "request_structured", delayed)

    async def disconnect():
        response = await routes.stream_project_operation(before["id"], "plan", RevisionRequest(revision=before["revision"]))
        iterator = response.body_iterator
        while True:
            event = json.loads(await anext(iterator))
            if event.get("stage") == "evaluation":
                break
        checkpoint = client.get(url).json()
        assert checkpoint["plan_generations"][-1]["critic_status"] == "pending"
        release.set()
        await asyncio.wait_for(iterator.aclose(), timeout=5)

    asyncio.run(disconnect())
    reopened = TestClient(create_app()).get(url).json()
    generation = reopened["plan_generations"][-1]
    assert generation["critic_status"] == "failed"
    assert (reopened["draft"] == before["draft"]) if existing else (reopened["draft"] == generation["draft"])


def test_accept_pending_proposal_blocks_late_critic_and_preserves_all_generated_plans(project_client, monkeypatch):
    client, provider = project_client
    before = ready(client, existing=True)
    url = f"/api/projects/{before['id']}"
    original = provider.request_structured
    accepted = None

    def accept_during_critic(request):
        nonlocal accepted
        if request.stage == "evaluation":
            checkpoint = client.get(url).json()
            generation = checkpoint["plan_generations"][-1]
            response = client.post(f"{url}/plans/{generation['id']}/accept", json={"revision": checkpoint["revision"]})
            assert response.status_code == 200
            accepted = response.json()
        return original(request)

    monkeypatch.setattr(provider, "request_structured", accept_during_critic)
    assert client.post(f"{url}/plan", json={"revision": before["revision"]}).status_code == 409
    assert client.get(url).json() == accepted
    assert accepted["feedback"] is accepted["feedback_source"] is None
    assert accepted["plan_generations"][-1]["critic_status"] == "pending"
    assert any(v["feedback_source"] == before["feedback_source"] for v in accepted["versions"])
    monkeypatch.setattr(provider, "request_structured", original)
    next_result = client.post(f"{url}/plan", json={"revision": accepted["revision"]}).json()
    assert next_result["plan_generations"][:-1] == accepted["plan_generations"]
    assert len({g["id"] for g in next_result["plan_generations"]}) == 3


def test_legacy_read_does_not_write_and_recovery_state_cannot_be_submitted_by_client(project_client):
    client, _ = project_client
    before = ready(client, existing=True)
    store = routes.get_project_store()
    raw = store.get(before["id"])
    raw.pop("plan_generations")
    stored = store.save(raw, before["revision"])
    url = f"/api/projects/{before['id']}"
    reopened = client.get(url).json()
    assert reopened["plan_generations"] == reopened["applicable_plan_ids"] == []
    assert reopened["draft"] == before["draft"] and reopened["feedback"] == before["feedback"]
    assert store.get(before["id"]) == stored
    for key in ["plan_generations", "applicable_plan_ids"]:
        assert client.put(url, json={**payload(reopened), key: []}).status_code == 422
    assert client.get(url).json() == reopened


@pytest.mark.parametrize("existing", [False, True])
def test_failed_planner_creates_no_draft_proposal_or_revision(project_client, monkeypatch, existing):
    client, provider = project_client
    before = ready(client, existing)
    url = f"/api/projects/{before['id']}"

    def fail(request):
        raise ProviderTimeoutError("planner failed")

    monkeypatch.setattr(provider, "request_structured", fail)
    assert client.post(f"{url}/plan", json={"revision": before["revision"]}).status_code == 504
    assert client.get(url).json() == before
