from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient
from test_projects import project_client, develop_project, payload, start_project  # noqa: F401

from app.main import create_app


def scene(title="Cảnh của tác giả"):
    return {"id": str(uuid4()), "title": title, "action": "  Cha đặt thư.\n\nCon nhìn, chưa mở.  ",
            "staging_choices": {"blocking": "Chừa lối ra."}}


def begin(client):
    project = develop_project(client, start_project(client))
    result = client.post(f"/api/projects/{project['id']}/scene-outline", json={
        "revision": project["revision"], "source_version_id": "current"})
    assert result.status_code == 200, result.text
    return project, result.json()


def update(project, scenes):
    return {**payload(project), "scene_outline": {
        "id": project["scene_outline"]["id"], "version": project["scene_outline"]["version"],
        "scenes": scenes,
    }}


def test_save_reopen_legacy_omission_and_m1_feedback_are_preserved(project_client):
    client, provider = project_client
    before, project = begin(client)
    url = f"/api/projects/{project['id']}"
    calls = len(provider.requests)
    source = deepcopy(project["scene_outline"]["source"])
    scenes = [scene(), scene()]
    response = client.put(url, json=update(project, scenes))
    assert response.status_code == 200, response.text
    saved = response.json()
    assert TestClient(create_app()).get(url).json() == saved
    assert [s["id"] for s in saved["scene_outline"]["scenes"]] == [s["id"] for s in scenes]
    assert saved["scene_outline"]["scenes"][0]["action"] == scenes[0]["action"]
    assert saved["scene_outline"]["version"] == 2
    assert saved["scene_outline"]["source"] == source
    assert saved["feedback_source"] == before["feedback_source"]
    assert saved["feedback_is_current"] == before["feedback_is_current"]
    assert len(provider.requests) == calls
    legacy_save = client.put(url, json={**payload(saved), "title": "Tên mới"}).json()
    assert legacy_save["scene_outline"] == saved["scene_outline"]
    assert legacy_save["scene_versions"] == saved["scene_versions"]
    assert legacy_save["scene_handoff"]["version"] == 2
    assert legacy_save["scene_handoff"]["scenes"] == saved["scene_outline"]["scenes"]
    reviewed = client.post(url + "/review", json={"revision": legacy_save["revision"]})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["scene_outline"] == saved["scene_outline"]
    assert reviewed.json()["scene_versions"] == saved["scene_versions"]


def test_two_windows_conflict_reorder_delete_restore_and_source_staleness(project_client):
    client, _ = project_client
    before, project = begin(client)
    url = f"/api/projects/{project['id']}"
    a, b = scene("A"), scene("B")
    first = client.put(url, json=update(project, [a, b])).json()
    assert client.put(url, json=update(project, [scene("Stale")])).status_code == 409
    assert client.get(url).json()["scene_outline"] == first["scene_outline"]
    reordered = client.put(url, json=update(first, [b, a])).json()
    assert [s["id"] for s in reordered["scene_outline"]["scenes"]] == [b["id"], a["id"]]
    empty = client.put(url, json=update(reordered, [])).json()
    assert empty["scene_handoff"] is None
    historical = next(v for v in empty["scene_versions"] if v["outline"]["scenes"]
                      and v["outline"]["scenes"][0]["id"] == a["id"])
    restored = client.post(f"{url}/scene-versions/{historical['id']}/restore",
                           json={"revision": empty["revision"]}).json()
    assert restored["scene_outline"]["version"] == empty["scene_outline"]["version"] + 1
    assert restored["draft"] == before["draft"]
    assert restored["scene_outline"]["scenes"] == first["scene_outline"]["scenes"]
    changed = payload(restored)
    changed["draft"]["logline"] = "Ý định hiện tại đã đổi."
    latest = client.put(url, json=changed).json()
    assert latest["scene_source_is_current"] is False
    assert latest["scene_outline"]["source"] == first["scene_outline"]["source"]
    assert latest["scene_outline"]["scenes"] == first["scene_outline"]["scenes"]


def test_source_selection_and_validation_cannot_replace_or_forge_outline(project_client):
    client, _ = project_client
    _, project = begin(client)
    url = f"/api/projects/{project['id']}"
    assert client.post(url + "/scene-outline", json={"revision": project["revision"]}).status_code == 409
    duplicate = scene()
    assert client.put(url, json=update(project, [duplicate, duplicate])).status_code == 422
    forged = update(project, [scene()])
    forged["scene_outline"]["source"] = {"id": "forged"}
    assert client.put(url, json=forged).status_code == 422
    forged = update(project, [scene()])
    forged["scene_outline"]["version"] += 1
    assert client.put(url, json=forged).status_code == 409
    assert client.put(url, json={**payload(project), "scene_outline": None}).status_code == 422
    assert client.get(url).json()["scene_outline"] == project["scene_outline"]
    other = develop_project(client, start_project(client))
    other_url = f"/api/projects/{other['id']}"
    changed = payload(other)
    changed["draft"]["logline"] = "Bản hiện tại khác bản lịch sử."
    other = client.put(other_url, json=changed).json()
    version = other["versions"][-1]
    picked = client.post(other_url + "/scene-outline", json={
        "revision": other["revision"], "source_version_id": version["id"]}).json()
    assert picked["scene_outline"]["source"]["draft"] == version["draft"]
    assert picked["draft"] == other["draft"]
    assert picked["scene_source_is_current"] is False
    blank = client.post("/api/projects").json()
    assert client.post(f"/api/projects/{blank['id']}/scene-outline",
                       json={"revision": blank["revision"]}).status_code == 422


def test_legacy_history_answers_remain_in_scene_source(project_client):
    from app.api.routes import projects as routes
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    changed = payload(project)
    changed["draft"]["logline"] = "Nội dung mới."
    project = client.put(url, json=changed).json()
    store = routes.get_project_store()
    raw = store.get(project["id"])
    historical = raw["versions"][-1]
    historical.pop("clarifications", None)
    raw = store.save(raw, project["revision"])
    picked = client.post(url + "/scene-outline", json={
        "revision": raw["revision"], "source_version_id": historical["id"]}).json()
    assert {a["question"]: a["answer"] for a in picked["scene_outline"]["source"]["context"]["clarifications"]} == {
        q: a for q, a in zip(historical["questions"], historical["answers"]) if a.strip()
    }
