from copy import deepcopy

from fastapi.testclient import TestClient
from test_projects import project_client, payload, develop_project, start_project  # noqa: F401
from test_scene_outline import begin, scene, update
from test_scene_suggestions import SceneProvider, suggest
from test_scene_staging import Provider, generate, use_payload

from app.api.routes import projects as routes
from app.main import create_app


def test_manual_handoff_uses_selected_history_not_current_m1(project_client):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    changed = payload(project)
    changed["draft"]["logline"] = "Story plan hiện tại khác nguồn được chọn."
    project = client.put(url, json=changed).json()
    version = project["versions"][-1]
    project = client.post(url + "/scene-outline", json={
        "revision": project["revision"], "source_version_id": version["id"]}).json()
    source = deepcopy(project["scene_outline"]["source"])
    calls = len(provider.requests)
    a, b = scene("Trùng tên"), scene("Trùng tên")
    b.update(viewer_intent="Giữ khoảng lặng.", keep_or_avoid="Không mở thư.",
             staging_choices={"lighting": "Tác giả chọn ánh sáng tản."})
    response = client.put(url, json=update(project, [b, a]))
    assert response.status_code == 200, response.text
    saved = response.json()
    handoff = saved["scene_handoff"]
    assert handoff == {"outline_id": saved["scene_outline"]["id"], "version": 2,
                       "project_revision": saved["revision"], "source_id": source["id"],
                       "scenes": saved["scene_outline"]["scenes"]}
    assert [s["id"] for s in handoff["scenes"]] == [b["id"], a["id"]]
    assert saved["scene_outline"]["source"] == source
    assert source["draft"] == version["draft"] and saved["draft"] == project["draft"]
    assert not saved["scene_source_is_current"]
    assert TestClient(create_app()).get(url).json()["scene_handoff"] == handoff
    assert len(provider.requests) == calls  # Saving/reading a handoff needs neither text nor image AI.
    forged = {**payload(saved), "scene_handoff": {**handoff, "source_id": "forged"}}
    assert client.put(url, json=forged).status_code == 422
    assert client.get(url).json()["scene_handoff"] == handoff


def test_ai_path_handoff_contains_only_saved_author_choices(project_client, monkeypatch):
    client, _ = project_client
    _, project = begin(client)
    url = f"/api/projects/{project['id']}"
    scenes = SceneProvider()
    monkeypatch.setattr(routes, "get_scene_provider", lambda: scenes)
    ready = suggest(client, project)[0].json()
    proposal = ready["scene_proposals"][-1]
    authored = deepcopy(proposal["scenes"])
    authored[0]["action"] = "  Con gái nhìn thư.\n\nChưa mở.  "
    saved = client.put(url, json={**update(ready, authored), "scene_proposal_id": proposal["id"]}).json()
    staging = Provider()
    monkeypatch.setattr(routes, "get_scene_provider", lambda: staging)
    ready = generate(client, saved)[0].json()
    batch = ready["staging_proposals"][-1]
    used, skipped, untouched = batch["staging_ideas"]
    ready = client.post(f"{url}/scene-proposals/{batch['id']}/ideas/{skipped['id']}/discard",
                        json={"revision": ready["revision"]}).json()
    preview = "Gợi ý tự chỉnh nhưng chưa nhận."
    ready = client.put(url, json={**payload(ready), "staging_idea_edits": {untouched["id"]: preview}}).json()
    assert ready["scene_handoff"]["scenes"] == saved["scene_handoff"]["scenes"]
    response = client.put(url, json=use_payload(ready, batch, used, "Tác giả chọn lùi một bước."))
    assert response.status_code == 200, response.text
    saved = response.json()
    handoff = saved["scene_handoff"]
    assert handoff["scenes"] == saved["scene_outline"]["scenes"]
    assert handoff["scenes"][0]["staging_choices"] == {used["field"]: "Tác giả chọn lùi một bước."}
    assert handoff["scenes"][0]["action"] == authored[0]["action"]
    assert saved["draft"] == project["draft"] and saved["feedback_source"] == project["feedback_source"]
    assert len(scenes.requests) == len(staging.requests) == 1
    assert TestClient(create_app()).get(url).json()["scene_handoff"] == handoff
    stale = client.put(url, json=use_payload(saved, batch, untouched, preview))
    assert stale.status_code == 409
    assert client.get(url).json()["scene_handoff"] == handoff


def test_incomplete_scene_and_stale_save_never_publish_a_handoff(project_client):
    client, provider = project_client
    _, project = begin(client)
    url = f"/api/projects/{project['id']}"
    calls = len(provider.requests)
    incomplete = scene()
    incomplete["action"] = " \n "
    saved = client.put(url, json=update(project, [incomplete])).json()
    assert saved["scene_handoff"] is None
    assert client.put(url, json=update(project, [scene("Không được ghi đè")])).status_code == 409
    assert client.get(url).json()["scene_handoff"] is None
    complete = client.put(url, json=update(saved, [scene("Đã hoàn thiện")])).json()
    handoff = complete["scene_handoff"]
    changed = payload(complete)
    changed["constraints"] = [*complete["constraints"], "Ý đồ hiện tại đã thay đổi."]
    latest = client.put(url, json=changed).json()
    assert not latest["scene_source_is_current"]
    assert latest["scene_handoff"]["scenes"] == handoff["scenes"]
    assert latest["scene_handoff"]["source_id"] == handoff["source_id"]
    assert len(provider.requests) == calls
