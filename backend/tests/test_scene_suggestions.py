from uuid import uuid4

import pytest
from test_scene_outline import begin, scene, update
from test_projects import project_client, payload  # noqa: F401
from app.api.routes import projects as routes
from app.api.schemas.scenes import SceneSuggestionResult
from app.application.ai_provider import (MalformedProviderResponseError, MissingProviderConfigurationError,
    ProviderMetadata, ProviderTimeoutError, StructuredResult)


class SceneProvider:
    metadata = ProviderMetadata("fake", "scenes", {"temperature": 0.3})
    def __init__(self):
        self.requests, self.count, self.failure = [], 2, None
        self.hook = lambda: None
    def request_structured(self, request):
        self.requests.append(request)
        self.hook()
        if self.failure:
            raise self.failure
        return StructuredResult(output=SceneSuggestionResult(scenes=[{
            "title": f"Đề xuất {i}", "action": "Cha đặt lá thư. Con gái nhìn, chưa mở.",
            "purpose": "Giữ quyền quyết định của con.", "transition": "Dừng trước câu trả lời.",
        } for i in range(self.count)]), model="scenes")


@pytest.fixture
def setup(project_client, monkeypatch):
    client, _ = project_client
    _, project = begin(client)
    provider = SceneProvider()
    monkeypatch.setattr(routes, "get_scene_provider", lambda: provider)
    return client, provider, project


def suggest(client, project, mode="list", target=None, request_id=None):
    body = {"revision": project["revision"], "request_id": request_id or str(uuid4()),
            "mode": mode, "target_scene_id": target, "instructions": "Giữ kết mở."}
    return client.post(f"/api/projects/{project['id']}/scene-suggestions", json=body), body


def test_durable_preview_idempotency_and_explicit_save(setup):
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    response, body = suggest(client, project)
    assert response.status_code == 200, response.text
    ready = response.json()
    proposal = ready["scene_proposals"][-1]
    assert ready["scene_outline"] == project["scene_outline"]
    assert ready["draft"] == project["draft"]
    assert proposal["status"] == "ready"
    assert proposal["prompt_version"] == "scene-suggestions-v3"
    import json
    list_input = json.loads(provider.requests[-1].input_text)
    assert list_input["scenes"] == project["scene_outline"]["scenes"]
    assert "reference_scenes" not in list_input
    assert provider.requests[-1].response_model.model_json_schema()["properties"]["scenes"]["maxItems"] == 60
    assert len({s["id"] for s in proposal["scenes"]}) == 2
    assert proposal["provider"] == "fake" and proposal["parameters"] == {"temperature": 0.3}
    assert ready["applicable_scene_proposal_ids"] == [body["request_id"]]
    assert client.post(url + "/scene-suggestions", json=body).status_code == 200
    assert len(provider.requests) == 1
    assert client.get(url).json() == ready
    edited = [{**proposal["scenes"][0], "action": "  Tác giả sửa.\n\nGiữ im lặng.  "}]
    saved = client.put(url, json={**update(ready, edited), "scene_proposal_id": proposal["id"]}).json()
    assert saved["scene_outline"]["scenes"] == edited
    assert saved["scene_proposals"][-1]["status"] == "applied"
    assert saved["scene_proposals"][-1]["scenes"] == proposal["scenes"]
    assert saved["applicable_scene_proposal_ids"] == []
    assert saved["feedback_source"] == project["feedback_source"]
    assert client.put(url, json={**update(saved, edited), "scene_proposal_id": proposal["id"]}).status_code == 409


def test_conflicting_author_counts_return_422_without_sending_ai(setup):
    client, provider, project = setup
    store = routes.get_project_store()
    raw = store.get(project['id'])
    raw['scene_outline']['source']['context']['constraints'] = ['Đúng hai cảnh.', 'Tối đa một cảnh.']
    store.save(raw, raw['revision'])
    project = client.get(f"/api/projects/{project['id']}").json()
    response, _ = suggest(client, project)
    assert response.status_code == 422 and 'Giới hạn số cảnh' in response.text
    assert not provider.requests
    saved = client.get(f"/api/projects/{project['id']}").json()
    assert saved['scene_proposals'][-1]['status'] == 'failed'
    assert saved['scene_outline'] == project['scene_outline']


def test_append_cannot_exceed_author_cap_but_develop_can_still_edit(setup):
    client, provider, project = setup
    store = routes.get_project_store()
    raw = store.get(project['id'])
    raw['scene_outline']['source']['context']['constraints'] = ['Tối đa một cảnh.']
    raw['scene_outline']['scenes'] = [scene()]
    store.save(raw, raw['revision'])
    project = client.get(f"/api/projects/{project['id']}").json()
    target = project['scene_outline']['scenes'][0]['id']
    before = project['scene_outline']['scenes']
    response, _ = suggest(client, project, 'append', target)
    assert response.status_code == 422 and not provider.requests
    project = client.get(f"/api/projects/{project['id']}").json()
    assert project['scene_outline']['scenes'] == before
    provider.count = 1
    response, _ = suggest(client, project, 'develop', target)
    assert response.status_code == 200 and len(provider.requests) == 1


def test_late_result_preserves_concurrent_author_edits(setup):
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    def edit():
        current = client.get(url).json()
        assert current["scene_proposals"][-1]["status"] == "pending"
        changed = {**update(current, [scene("Cảnh tác giả vừa viết")]), "title": "Tên mới"}
        assert client.put(url, json=changed).status_code == 200
    provider.hook = edit
    response, _ = suggest(client, project)
    latest = response.json()
    assert latest["title"] == "Tên mới"
    assert latest["scene_outline"]["scenes"][0]["title"] == "Cảnh tác giả vừa viết"
    assert latest["scene_proposals"][-1]["status"] == "ready"
    assert latest["applicable_scene_proposal_ids"] == []
    assert client.put(url, json={**update(latest, []), "scene_proposal_id": latest["scene_proposals"][-1]["id"]}).status_code == 409


@pytest.mark.parametrize("error", [MissingProviderConfigurationError("missing"), ProviderTimeoutError("timeout"),
    MalformedProviderResponseError("bad", raw_output="bad json")])
def test_failed_request_recorded_no_retry_manual_edit_works(setup, error):
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    provider.failure = error
    response, body = suggest(client, project)
    assert response.status_code in {502, 503, 504}
    latest = client.get(url).json()
    assert latest["scene_proposals"][-1]["status"] == "failed"
    assert latest["scene_proposals"][-1]["error"] == type(error).__name__
    assert latest["scene_proposals"][-1]["prompt_version"] == "scene-suggestions-v3"
    assert latest["scene_outline"] == project["scene_outline"]
    assert client.post(url + "/scene-suggestions", json=body).status_code == 200
    assert len(provider.requests) == 1
    assert client.put(url, json=update(latest, [scene()])).status_code == 200


def test_single_scene_modes_and_no_regeneration(setup):
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    original = {**scene(), "viewer_intent": "Còn xa cách", "keep_or_avoid": "Không nói tha thứ"}
    project = client.put(url, json=update(project, [original])).json()
    assert suggest(client, project)[0].status_code == 422
    assert not provider.requests
    provider.count = 1
    result, _ = suggest(client, project, "develop", original["id"])
    latest = result.json()
    assert provider.requests[-1].response_model.model_json_schema()["properties"]["scenes"]["maxItems"] == 1
    import json
    develop_input = json.loads(provider.requests[-1].input_text)
    assert develop_input["scenes"] == project["scene_outline"]["scenes"]
    assert "reference_scenes" not in develop_input
    proposed = latest["scene_proposals"][-1]["scenes"][0]
    for key in ("id", "viewer_intent", "keep_or_avoid", "staging_choices"):
        assert proposed[key] == original[key]
    appended, _ = suggest(client, latest, "append", original["id"])
    assert provider.requests[-1].response_model.model_json_schema()["properties"]["scenes"]["maxItems"] == 1
    assert appended.json()["scene_proposals"][-1]["scenes"][0]["id"] != original["id"]
    assert appended.json()["scene_outline"] == project["scene_outline"]
    provider.count = 2
    assert suggest(client, appended.json(), "develop", original["id"])[0].status_code == 502


def test_pending_duplicate_same_id_and_different_request(setup):
    client, provider, project = setup
    request_id = str(uuid4())
    def duplicate():
        result, _ = suggest(client, project, request_id=request_id)
        assert result.status_code == 200
        assert result.json()["scene_proposals"][-1]["status"] == "pending"
    provider.hook = duplicate
    result, body = suggest(client, project, request_id=request_id)
    assert result.status_code == 200 and len(provider.requests) == 1
    body["instructions"] = "Khác"
    assert client.post(f"/api/projects/{project['id']}/scene-suggestions", json=body).status_code == 409


def test_stream_progress_and_discard(setup):
    import json
    client, _, project = setup
    url = f"/api/projects/{project['id']}"
    body = {"revision": project["revision"], "request_id": str(uuid4()), "mode": "list"}
    result = client.post(url + "/scene-suggestions/stream", json=body)
    events = [json.loads(line) for line in result.text.splitlines() if line.strip()]
    stages = [e["stage"] for e in events if e["type"] == "progress" and e["status"] == "completed"]
    assert stages == ["scene_checkpoint", "scene_source", "scene_generation", "scene_validation", "scene_proposal_save"]
    assert events[-1]["type"] == "result"
    latest = events[-1]["project"]
    proposal = latest["scene_proposals"][-1]
    discarded = client.post(url + f"/scene-proposals/{proposal['id']}/discard", json={"revision": latest["revision"]}).json()
    assert discarded["scene_proposals"][-1]["status"] == "discarded"
    assert discarded["scene_outline"] == project["scene_outline"]


def test_changed_m1_and_unsaved_m1_cannot_accept_old_proposal(setup):
    client, _, project = setup
    result, _ = suggest(client, project)
    ready = result.json()
    url = f"/api/projects/{project['id']}"
    proposal = ready["scene_proposals"][-1]
    changed = update(ready, proposal["scenes"])
    changed["scene_proposal_id"] = proposal["id"]
    changed["draft"]["logline"] = "Một ý đồ khác."
    assert client.put(url, json=changed).status_code == 409
    changed = payload(ready)
    changed["draft"]["logline"] = "Một ý đồ khác."
    latest = client.put(url, json=changed).json()
    assert latest["applicable_scene_proposal_ids"] == []
    assert client.put(url, json={**update(latest, proposal["scenes"]), "scene_proposal_id": proposal["id"]}).status_code == 409


def test_discard_while_pending_keeps_late_output_without_reactivating_it(setup):
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    request_id = str(uuid4())
    def discard():
        current = client.get(url).json()
        result = client.post(url + f"/scene-proposals/{request_id}/discard", json={"revision": current["revision"]})
        assert result.status_code == 200
    provider.hook = discard
    result, body = suggest(client, project, request_id=request_id)
    latest = result.json()
    assert latest["scene_proposals"][-1]["status"] == "discarded"
    assert len(latest["scene_proposals"][-1]["scenes"]) == 2
    assert latest["applicable_scene_proposal_ids"] == []
    assert latest["scene_outline"] == project["scene_outline"]
    assert client.post(url + "/scene-suggestions", json=body).status_code == 200
    assert len(provider.requests) == 1


def test_edited_preview_saves_separately_without_changing_original_or_outline(setup):
    client, _, project = setup
    ready = suggest(client, project)[0].json()
    url = f"/api/projects/{project['id']}"
    proposal = ready["scene_proposals"][-1]
    preview = [{**proposal["scenes"][0], "action": "  Bản xem trước do tác giả chỉnh.  "}]
    saved = client.put(url, json={**payload(ready), "scene_proposal_previews": {proposal["id"]: preview}})
    assert saved.status_code == 200, saved.text
    latest = client.get(url).json()
    assert latest["scene_proposals"][-1]["preview_scenes"] == preview
    assert latest["scene_proposals"][-1]["scenes"] == proposal["scenes"]
    assert latest["scene_outline"] == project["scene_outline"]
    assert latest["applicable_scene_proposal_ids"] == [proposal["id"]]
    invalid = [{**preview[0], "id": str(uuid4())}]
    assert client.put(url, json={**payload(latest), "scene_proposal_previews": {proposal["id"]: invalid}}).status_code == 422
    assert client.put(url, json={**payload(latest), "scene_proposal_previews": {proposal["id"]: preview * 2}}).status_code == 422
    assert client.get("/api/datasets/samples").status_code == 200
    from app.application.dataset import get_dataset_store
    records = [r for r in get_dataset_store().records() if r["operation"] == "scene_suggestions"]
    assert len(records) == 1 and records[0]["steps"][0]["raw_output"] is None
    assert records[0]["steps"][0]["request"]["prompt_sha256"]


def test_single_scene_schema_rejects_zero_or_many_without_slicing():
    from pydantic import ValidationError
    from app.api.schemas.scenes import SingleSceneSuggestionResult
    item = {"title": "Cảnh", "action": "Cha đặt thư."}
    assert len(SingleSceneSuggestionResult.model_validate({"scenes": [item]}).scenes) == 1
    for invalid in ([], [item, item]):
        with pytest.raises(ValidationError):
            SingleSceneSuggestionResult.model_validate({"scenes": invalid})
    schema = SingleSceneSuggestionResult.model_json_schema()["properties"]["scenes"]
    assert schema["minItems"] == schema["maxItems"] == 1
    assert len(SceneSuggestionResult.model_validate({"scenes": [item, item]}).scenes) == 2


@pytest.mark.parametrize("scene_count,target_index", [(3, 0), (3, None), (0, None)])
def test_append_input_marks_readonly_references_and_exact_insertion_without_changing_source(setup, scene_count, target_index):
    import json
    client, provider, project = setup
    url = f"/api/projects/{project['id']}"
    scenes = [scene(f"Cảnh nguồn {i}") for i in range(scene_count)]
    project = client.put(url, json=update(project, scenes)).json()
    source = project["scene_outline"]
    provider.count = 1
    target = source["scenes"][target_index]["id"] if target_index is not None else None
    response, _ = suggest(client, project, "append", target)
    assert response.status_code == 200, response.text
    request = provider.requests[-1]
    data = json.loads(request.input_text)
    assert "scenes" not in data  # Only the response uses this name in append mode.
    assert data["reference_scenes"] == source["scenes"]
    after = target_index if target_index is not None else scene_count - 1
    assert data["insertion_context"] == {
        "after_scene_id": source["scenes"][after]["id"] if after >= 0 else None,
        "before_scene_id": source["scenes"][after + 1]["id"] if after + 1 < scene_count else None,
    }
    assert data["story_plan"] == source["source"]["draft"]
    assert data["author_intent"] == source["source"]["context"]
    assert request.response_model.model_json_schema()["properties"]["scenes"]["maxItems"] == 1
    assert "reference_scenes are read-only context" in request.instructions
    assert "Put the new visible action in action itself" in request.instructions
    result = response.json()
    assert result["scene_outline"] == source
    assert result["scene_proposals"][-1]["source_outline"] == source
    assert result["scene_proposals"][-1]["prompt_version"] == "scene-suggestions-v3"
