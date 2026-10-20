import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from test_generate_workflow import FakeProvider

from app.api.routes import projects as project_routes
from app.application.project_store import ProjectStore
from app.infrastructure.openai_provider import MissingProviderConfigurationError
from app.main import create_app


@pytest.fixture
def project_client(tmp_path, monkeypatch):
    store_path = tmp_path / "projects.sqlite3"
    monkeypatch.setattr(project_routes, "get_project_store", lambda: ProjectStore(store_path))
    provider = FakeProvider()
    monkeypatch.setattr(
        "app.application.workflow.OpenAIProvider.from_env", classmethod(lambda cls: provider)
    )
    return TestClient(create_app()), provider


def payload(project):
    return {
        key: deepcopy(project[key])
        for key in ("revision", "title", "idea", "constraints", "answers", "draft")
    }


def start_project(client):
    response = client.post("/api/projects")
    assert response.status_code == 201
    project = response.json()
    data = payload(project)
    data.update(
        title="Chuyến đi đầu tiên",
        idea="Một người cha muốn gặp con gái trước khi cô rời Việt Nam.",
        constraints=["Only one apartment", "Two characters"],
    )
    return client.put(f"/api/projects/{project['id']}", json=data).json()


def develop_project(client, project):
    url = f"/api/projects/{project['id']}"
    project = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    data = payload(project)
    data["answers"] = ["She leaves tomorrow", "He wants to apologize, not stop her"]
    project = client.put(url, json=data).json()
    response = client.post(f"{url}/plan", json={"revision": project["revision"]})
    assert response.status_code == 200, response.text
    return response.json()


def test_questions_gate_generation_and_review_uses_the_saved_edited_draft(project_client):
    client, provider = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    assert client.post(f"{url}/plan", json={"revision": project["revision"]}).status_code == 422
    project = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    assert [item.response_model.__name__ for item in provider.requests] == ["_ReasoningOutput"]
    assert project["draft"] is None
    assert client.post(f"{url}/plan", json={"revision": project["revision"]}).status_code == 422
    data = payload(project)
    data["answers"] = ["She leaves tomorrow", "He wants to apologize, not stop her"]
    project = client.put(url, json=data).json()
    project = client.post(f"{url}/plan", json={"revision": project["revision"]}).json()
    assert len(provider.requests) == 3
    assert "He wants to apologize" in provider.requests[1].input_text
    assert "Only one apartment" in provider.requests[1].input_text
    assert "He wants to apologize" in provider.requests[2].input_text
    assert project["feedback_is_current"] is True
    original_draft = deepcopy(project["draft"])
    data = payload(project)
    data["draft"]["sections"][5]["content"] = "EDITED_ENDING: He stays home and sends her a letter."
    project = client.put(url, json=data).json()
    assert project["feedback_is_current"] is False
    assert project["versions"][0]["draft"] == original_draft
    edited_draft = deepcopy(project["draft"])
    project = client.post(f"{url}/review", json={"revision": project["revision"]}).json()
    assert provider.requests[-1].response_model.__name__ == "_EvaluationOutput"
    assert "EDITED_ENDING" in provider.requests[-1].input_text
    assert "He wants to apologize" in provider.requests[-1].input_text
    assert "Only one apartment" in provider.requests[-1].input_text
    review_input = provider.requests[-1].input_text
    context = json.loads(
        review_input.split("Creator intent and decisions:\n", 1)[1].split("\n\n", 1)[0]
    )
    assert context["clarifications"] == [
        {"question": question, "answer": answer}
        for question, answer in zip(project["analysis"]["missing_information"], project["answers"])
    ]
    current_draft = json.loads(
        review_input.split("Current draft (JSON data):\n", 1)[1].split("\n\n", 1)[0]
    )
    assert current_draft == {
        "title": edited_draft["title"],
        "logline": edited_draft["logline"],
        "sections": [
            {"title": section["title"], "content": section["content"]}
            for section in edited_draft["sections"]
        ],
    }
    assert "Resolve the short film through a visible choice or image." not in review_input
    assert "He gives Linh his blessing at the airport curb." not in review_input
    assert project["draft"] == edited_draft
    assert project["feedback_is_current"] is True
    assert len(project["versions"]) == 2
    reopened = TestClient(create_app()).get(url).json()
    assert reopened["draft"] == edited_draft
    assert reopened["versions"] == project["versions"]
    assert client.get("/api/projects").json()[0]["title"] == "Chuyến đi đầu tiên"


def test_stale_save_cannot_overwrite_another_windows_work(project_client):
    client, _ = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["title"] = "Saved in another window"
    assert client.put(url, json=data).status_code == 200
    data["title"] = "Stale overwrite"
    assert client.put(url, json=data).status_code == 409
    assert client.get(url).json()["title"] == "Saved in another window"


def test_failed_review_preserves_edited_draft_and_old_feedback(project_client, monkeypatch):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["draft"]["logline"] = "A new logline written by the creator."
    project = client.put(url, json=data).json()

    def missing_key():
        raise MissingProviderConfigurationError("secret must not leak")

    monkeypatch.setattr(project_routes, "get_story_generation_service", missing_key)
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 503
    assert "secret" not in response.text
    stored = client.get(url).json()
    assert stored["draft"] == project["draft"]
    assert stored["feedback"] == project["feedback"]
    assert stored["feedback_is_current"] is False


def test_changing_brief_invalidates_questions_without_discarding_work(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["idea"] = "Một người mẹ chờ con trai."
    changed = client.put(url, json=data).json()
    assert changed["analysis"] is None
    assert changed["answers"] == []
    assert changed["draft"] == project["draft"]
    assert changed["versions"] == project["versions"]
    assert changed["feedback_is_current"] is False
    assert client.post(f"{url}/plan", json={"revision": changed["revision"]}).status_code == 422


def test_restoring_a_plan_keeps_the_replaced_manual_draft(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    original = deepcopy(project["draft"])
    data = payload(project)
    data["draft"]["logline"] = "An unreviewed manual revision."
    changed = client.put(url, json=data).json()
    data = payload(changed)
    data["draft"] = original
    restored = client.put(url, json=data).json()
    assert restored["draft"] == original
    assert any(
        version["draft"]["logline"] == "An unreviewed manual revision."
        for version in restored["versions"]
    )


def test_missing_projects_and_invalid_drafts_are_rejected(project_client):
    client, _ = project_client
    assert client.get("/api/projects/missing").status_code == 404
    project = start_project(client)
    data = payload(project)
    data["draft"] = {"title": "", "logline": "", "sections": []}
    assert client.put(f"/api/projects/{project['id']}", json=data).status_code == 422


def test_late_ai_response_cannot_replace_newer_saved_work(project_client, monkeypatch):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    original_request = provider.request_structured

    def save_while_ai_is_running(request):
        if request.response_model.__name__ == "_EvaluationOutput":
            latest = client.get(url).json()
            data = payload(latest)
            data["draft"]["logline"] = "A newer edit from another window."
            assert client.put(url, json=data).status_code == 200
        return original_request(request)

    monkeypatch.setattr(provider, "request_structured", save_while_ai_is_running)
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 409
    latest = client.get(url).json()
    assert latest["draft"]["logline"] == "A newer edit from another window."
    assert latest["feedback_is_current"] is False


def test_incomplete_edits_can_be_saved_without_requesting_ai_feedback(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    for section in data["draft"]["sections"]:
        section["content"] = ""
    response = client.put(url, json=data)
    assert response.status_code == 200
    saved = response.json()
    assert client.get(url).json()["draft"] == saved["draft"]
    assert client.post(f"{url}/review", json={"revision": saved["revision"]}).status_code == 422


def test_changing_brief_keeps_even_newly_edited_answers_before_a_plan_exists(project_client):
    client, _ = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    project = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    data = payload(project)
    data["answers"] = ["An answer not saved separately yet.", "A detail I want to keep."]
    data["idea"] = "Một ý tưởng đã được sửa lại."
    changed = client.put(url, json=data).json()
    assert changed["analysis"] is None
    assert changed["draft"] is None
    history = changed["clarification_history"][-1]
    assert history["idea"] == project["idea"]
    assert history["questions"] == project["analysis"]["missing_information"]
    assert history["answers"] == data["answers"]
    assert client.get(url).json()["clarification_history"] == changed["clarification_history"]


def test_reanalysis_does_not_erase_answers_to_unchanged_questions(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    result = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    assert result["answers"] == project["answers"]


def test_same_answer_text_for_different_questions_cannot_revalidate_old_feedback(
    project_client, monkeypatch
):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    original_request = provider.request_structured

    def ask_different_questions(request):
        result = original_request(request)
        if request.response_model.__name__ == "_ReasoningOutput":
            result.output.missing_information = ["When does the story end?", "What does she want?"]
        return result

    monkeypatch.setattr(provider, "request_structured", ask_different_questions)
    analyzed = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    data = payload(analyzed)
    data["answers"] = project["answers"]
    saved = client.put(url, json=data).json()
    assert saved["feedback_is_current"] is False
    assert saved["versions"][0]["questions"] == project["analysis"]["missing_information"]


def test_omitting_saved_content_cannot_silently_clear_it(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    response = client.put(
        url, json={"revision": project["revision"], "title": "Rename only", "idea": project["idea"]}
    )
    assert response.status_code == 422
    assert client.get(url).json() == project


def test_answers_cannot_be_saved_without_their_corresponding_questions(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["answers"] = ["Only one answer for two questions"]
    assert client.put(url, json=data).status_code == 422
    assert client.get(url).json() == project


def test_existing_database_records_keep_their_drafts_and_feedback(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    store = project_routes.get_project_store()
    legacy = store.get(project["id"])
    legacy.pop("clarification_history", None)
    for version in legacy["versions"]:
        version.pop("questions", None)
    old_content = json.loads(legacy["reviewed_content"])
    old_content.pop("questions", None)
    legacy["reviewed_content"] = json.dumps(old_content, ensure_ascii=False, sort_keys=True)
    stored = store.save(legacy, project["revision"])
    response = client.get(f"/api/projects/{project['id']}")
    assert response.status_code == 200
    reopened = response.json()
    assert reopened["draft"] == project["draft"]
    assert reopened["feedback"] == project["feedback"]
    assert reopened["feedback_is_current"] is False
    assert reopened["clarification_history"] == []
    assert reopened["versions"][0]["questions"] == []
    assert store.get(project["id"]) == stored
