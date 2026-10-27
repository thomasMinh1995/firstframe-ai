import json
from uuid import uuid4
import pytest
from pydantic import BaseModel
from test_projects import project_client, payload  # noqa: F401
from test_scene_outline import begin, scene, update
from app.api.routes import projects as routes
from app.application.ai_provider import ProviderMetadata, ProviderTimeoutError, StructuredResult


class RawOutput(BaseModel):
    ideas: list[dict]
    question: str = ""


class Provider:
    metadata = ProviderMetadata("fake", "staging-model")
    def __init__(self):
        self.requests, self.bad, self.error, self.empty = [], None, None, False
        self.hook = lambda: None
    def request_structured(self, request):
        self.requests.append(request); self.hook()
        if self.error:
            raise self.error
        data = json.loads(request.input_text)
        source = next(s for s in data["sources"] if s["id"] == f"scene:{data['target_scene_id']}:action")
        ideas = [{"field": field, "evidence": [{"source_id": source["id"], "quote": source["text"][:80]}],
                  "reason": "Chi tiết đặt thư cho phép giữ khoảng cách.", "suggestion": text,
                  "purpose": "Giữ quyền quyết định của con."} for field, text in (
                      ("blocking", "Cha rút tay, để lối đi trống."), ("setting", "Thư ở khoảng trống giữa hai người."),
                      ("composition", "Giữ hai người cùng khung, thư ở giữa."))]
        if self.bad:
            self.bad(ideas, data)
        output = RawOutput(ideas=[] if self.empty else ideas, question="Bạn muốn người xem cảm nhận điều gì?" if self.empty else "")
        return StructuredResult(output=output, model="staging-model", raw_output=output.model_dump_json())


@pytest.fixture
def staging(project_client, monkeypatch):
    client, _ = project_client; _, project = begin(client)
    project = client.put(f"/api/projects/{project['id']}", json=update(project, [scene("Lá thư"), scene("Sau đó")])).json()
    provider = Provider(); monkeypatch.setattr(routes, "get_scene_provider", lambda: provider)
    return client, provider, project


def generate(client, project, request_id=None):
    body = {"revision": project["revision"], "request_id": request_id or str(uuid4()), "mode": "staging",
            "target_scene_id": project["scene_outline"]["scenes"][0]["id"], "instructions": ""}
    return client.post(f"/api/projects/{project['id']}/scene-suggestions", json=body), body


def use_payload(project, batch, idea, text):
    scenes = json.loads(json.dumps(project["scene_outline"]["scenes"]))
    next(s for s in scenes if s["id"] == batch["target_scene_id"])["staging_choices"][idea["field"]] = text
    return {**update(project, scenes), "staging_use": {"proposal_id": batch["id"], "idea_id": idea["id"], "value": text}}


def test_separate_durable_three_groups_and_idempotency(staging):
    client, provider, project = staging; response, body = generate(client, project)
    assert response.status_code == 200, response.text
    latest = response.json(); batch = latest["staging_proposals"][-1]
    assert latest["scene_outline"] == project["scene_outline"] and latest["draft"] == project["draft"]
    assert latest["scene_proposals"] == project["scene_proposals"]  # Legacy clients never see the new mode in their old pool.
    assert batch["prompt_version"] == "scene-staging-v1"
    assert {i["field"] for i in batch["staging_ideas"]} == {"blocking", "setting", "composition"}
    assert len({i["id"] for i in batch["staging_ideas"]}) == 3
    texts = {s["id"]: s["text"] for s in batch["staging_sources"]}
    assert all(e["quote"] in texts[e["source_id"]] for i in batch["staging_ideas"] for e in i["evidence"])
    url = f"/api/projects/{project['id']}"
    assert client.get(url).json() == latest
    assert client.post(url + "/scene-suggestions", json=body).status_code == 200 and len(provider.requests) == 1
    assert latest["feedback_source"] == project["feedback_source"]


@pytest.mark.parametrize("bad", [
    lambda ideas, data: ideas[0].update(field="action"),
    lambda ideas, data: ideas[0]["evidence"][0].update(quote="Không có trong nguồn"),
    lambda ideas, data: ideas[0]["evidence"][0].update(source_id="scene:forged:action"),
    lambda ideas, data: ideas[0]["evidence"][0].update(quote=" "),
    lambda ideas, data: ideas[0].update(evidence=[{"source_id":"intent:idea", "quote":next(s["text"] for s in data["sources"] if s["id"]=="intent:idea")}]),
])
def test_wrong_field_or_quotes_reject_entire_result_keep_source_and_raw(staging, bad):
    client, provider, project = staging; provider.bad = bad
    response, body = generate(client, project); assert response.status_code == 502, response.text
    url = f"/api/projects/{project['id']}"; latest = client.get(url).json()
    assert latest["scene_outline"] == project["scene_outline"]
    assert latest["staging_proposals"][-1]["status"] == "failed" and not latest["staging_proposals"][-1]["staging_ideas"]
    assert client.post(url + "/scene-suggestions", json=body).status_code == 200 and len(provider.requests) == 1
    from app.application.dataset import get_dataset_store
    assert get_dataset_store().records()[-1]["steps"][0]["raw_output"]


def test_edit_use_only_one_field_and_remaining_ideas_stale(staging):
    client, _, project = staging; latest = generate(client, project)[0].json()
    batch = latest["staging_proposals"][-1]; idea, other = batch["staging_ideas"][:2]
    url = f"/api/projects/{project['id']}"; text = "  Cha tự lùi.\n\nGiữ lối đi.  "
    edited = client.put(url, json={**payload(latest), "staging_idea_edits": {idea["id"]: text}}).json()
    assert edited["scene_outline"] == project["scene_outline"]
    assert edited["staging_proposals"][-1]["staging_ideas"][0]["preview_text"] == text
    assert edited["staging_proposals"][-1]["staging_ideas"][0]["suggestion"] == idea["suggestion"]
    response = client.put(url, json=use_payload(edited, batch, idea, text)); assert response.status_code == 200, response.text
    saved = response.json(); expected = use_payload(edited, batch, idea, text)["scene_outline"]["scenes"]
    assert saved["scene_outline"]["scenes"] == expected
    for key in ("draft", "feedback_source"):
        assert saved[key] == project[key]
    assert saved["scene_outline"]["source"] == project["scene_outline"]["source"]
    applied = saved["staging_proposals"][-1]["staging_ideas"][0]
    assert applied["status"] == "applied" and applied["applied_text"] == text
    assert saved["staging_proposals"][-1]["source_outline"] == batch["source_outline"]
    assert saved["staging_proposals"][-1]["staging_ideas"][1]["status"] == "available"
    assert not saved["applicable_scene_proposal_ids"]
    assert client.put(url, json=use_payload(saved, batch, other, "Cố dùng ý cũ")).status_code == 409
    assert client.put(url, json=use_payload(edited, batch, idea, text)).status_code == 409


def test_cannot_apply_batch_or_change_action_discard_changes_no_scene(staging):
    client, _, project = staging; latest = generate(client, project)[0].json()
    batch = latest["staging_proposals"][-1]; idea = batch["staging_ideas"][0]; url = f"/api/projects/{project['id']}"
    forged = use_payload(latest, batch, idea, "Dàn cảnh"); forged["scene_outline"]["scenes"][0]["action"] = "Đổi diễn tiến"
    assert client.put(url, json=forged).status_code == 409
    assert client.put(url, json={**update(latest, latest["scene_outline"]["scenes"]), "scene_proposal_id": batch["id"]}).status_code == 422
    discarded = client.post(f"{url}/scene-proposals/{batch['id']}/ideas/{idea['id']}/discard", json={"revision": latest["revision"]}).json()
    assert discarded["scene_outline"] == project["scene_outline"] and discarded["staging_proposals"][-1]["staging_ideas"][0]["status"] == "discarded"
    assert client.put(url, json=use_payload(discarded, batch, idea, "Dùng ý đã bỏ")).status_code == 409


def test_empty_failure_and_late_result_allow_manual_work(staging):
    client, provider, project = staging; provider.empty = True
    latest = generate(client, project)[0].json(); batch = latest["staging_proposals"][-1]
    assert not batch["staging_ideas"] and batch["staging_question"]
    provider.empty = False; provider.error = ProviderTimeoutError("timeout")
    assert generate(client, latest)[0].status_code == 504
    url = f"/api/projects/{project['id']}"; latest = client.get(url).json()
    edited = client.put(url, json=update(latest, [scene("Tự viết sau lỗi")])).json()
    provider.error = None
    def edit():
        current = client.get(url).json()
        assert client.put(url, json=update(current, [scene("Bản mới trong khi AI chạy")])).status_code == 200
    provider.hook = edit; result = generate(client, edited)[0].json()
    assert result["scene_outline"]["scenes"][0]["title"] == "Bản mới trong khi AI chạy"
    assert result["staging_proposals"][-1]["status"] == "ready" and not result["applicable_scene_proposal_ids"]


def test_legacy_save_keeps_staging_and_discard_pending_does_not_reactivate_late_batch(staging):
    client, provider, project = staging; url = f"/api/projects/{project['id']}"; request_id = str(uuid4())
    def discard_pending():
        pending = client.get(url).json()
        assert pending["scene_proposals"] == []
        legacy = client.put(url, json={**payload(pending), "title": "Tên của tác giả"}).json()
        assert legacy["staging_proposals"] == pending["staging_proposals"]
        response = client.post(f"{url}/scene-proposals/{request_id}/discard", json={"revision": legacy["revision"]})
        assert response.status_code == 200
    provider.hook = discard_pending
    result, _ = generate(client, project, request_id)
    assert result.status_code == 200, result.text
    latest = result.json()
    assert latest["title"] == "Tên của tác giả" and latest["scene_proposals"] == []
    assert latest["staging_proposals"][-1]["status"] == "discarded"
    assert len(latest["staging_proposals"][-1]["staging_ideas"]) == 3
    assert latest["scene_outline"] == project["scene_outline"]
    assert not latest["applicable_scene_proposal_ids"]
