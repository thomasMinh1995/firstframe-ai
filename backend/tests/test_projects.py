import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from test_generate_workflow import FakeProvider

from app.api.routes import projects as project_routes
from app.application.ai_provider import MissingProviderConfigurationError
from app.application.project_store import ProjectStore
from app.main import create_app


@pytest.fixture
def project_client(tmp_path, monkeypatch):
    store_path = tmp_path / "projects.sqlite3"
    monkeypatch.setattr(project_routes, "get_project_store", lambda: ProjectStore(store_path))
    provider = FakeProvider()
    monkeypatch.setattr(
        "app.application.workflow.create_provider", lambda: provider
    )
    return TestClient(create_app()), provider


def payload(project):
    return {
        key: deepcopy(project[key])
        for key in ("revision", "title", "idea", "constraints", "answers", "draft")
    }


def card_input(project):
    card = project["author_context"]
    return {"idea": card["idea"], "constraints": card["constraints"], "clarifications": [
        {"question": item["question"], "answer": item["answer"]}
        for item in card["clarifications"]
    ]}


def critic_author(request):
    if "Card review context (JSON data):\n" not in request.input_text:
        return json.loads(request.input_text.split("Creator intent and decisions:\n", 1)[1].split("\n\n", 1)[0])
    context = json.loads(request.input_text.split("Card review context (JSON data):\n", 1)[1])
    return {"idea": context["decisions"][0]["text"],
            "constraints": [d["text"] for d in context["decisions"] if d["id"].startswith("constraint-")],
            "clarifications": [{"question": d["question"], "answer": d["text"]}
                               for d in context["decisions"] if d["id"].startswith("answer-")]}


def test_author_card_targets_the_last_effective_answer_to_a_repeated_question(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    store = project_routes.get_project_store()
    raw = store.get(project["id"])
    raw["analysis"]["missing_information"] = ["Điều cần giữ?", "Điều cần giữ?"]
    raw["answers"] = ["Câu trước", "Câu hiệu lực sau cùng"]
    store.save(raw, project["revision"])
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert reopened["author_context"]["clarifications"] == [{
        "question": "Điều cần giữ?", "answer": "Câu hiệu lực sau cùng", "input_index": 1,
    }]


def test_author_card_and_feedback_sources_keep_a_when_author_saves_b(project_client):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    source_a = deepcopy(project["feedback_source"])
    assert source_a["context"] == project["author_context"]
    assert source_a["revision"] == project["revision"] - 1
    for request in provider.requests[-2:]:
        intent = critic_author(request)
        assert intent == card_input(project)
    # A response projection cannot be supplied by a client, including through an old full-project PUT.
    bad = {**payload(project), "author_context": {"idea": "AI proposes this"}}
    assert client.put(url, json=bad).status_code == 422
    assert client.get(url).json() == project
    data = payload(project)
    data["idea"] = "Một người mẹ chờ con trong căn bếp, không có cãi vã."
    data["constraints"] = ["Giữ kết thúc mở", "Không tự thêm hòa giải"]
    data["draft"]["logline"] = "Bản sửa thủ công vẫn phải được giữ."
    changed = client.put(url, json=data).json()
    assert changed["author_context"] == {
        "idea": data["idea"], "constraints": data["constraints"],
        "clarifications": [], "pending_questions": [],
    }
    assert changed["feedback_source"] == source_a
    assert changed["feedback"] == project["feedback"]
    assert changed["feedback_is_current"] is False
    assert any(v["feedback_source"] == source_a for v in changed["versions"])
    # A stale save does not change the card or rebind the feedback's source.
    assert client.put(url, json=payload(project)).status_code == 409
    assert client.get(url).json() == changed
    reviewed = client.post(f"{url}/review", json={"revision": changed["revision"]}).json()
    intent = critic_author(provider.requests[-1])
    assert intent == card_input(reviewed)
    assert reviewed["feedback_source"]["context"] == changed["author_context"]
    assert reviewed["feedback_source"]["artifact_id"] != source_a["artifact_id"]
    assert reviewed["feedback_source"]["draft"] == data["draft"]
    assert any(v["feedback_source"] == source_a for v in reviewed["versions"])
    # Restore changes the working draft, not either feedback snapshot or its revision.
    restore = payload(reviewed)
    restore["draft"] = source_a["draft"]
    restored = client.put(url, json=restore).json()
    assert restored["feedback_source"] == reviewed["feedback_source"]
    assert restored["feedback_is_current"] is False
    store = project_routes.get_project_store()
    stored = store.get(project["id"])
    assert "author_context" not in stored, "the current card is a read projection, not a second store"
    assert client.get(url).json() == restored
    assert store.get(project["id"]) == stored, "opening cards must not write or migrate data"


@pytest.mark.parametrize("corruption", ["missing", "shape", "project", "artifact", "context", "key", "draft", "revision"])
def test_unverifiable_feedback_source_stays_missing_without_losing_work(project_client, corruption):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    store = project_routes.get_project_store()
    raw = store.get(project["id"])
    if corruption == "missing":
        raw.pop("feedback_source")
        for version in raw["versions"]:
            version.pop("feedback_source", None)
    elif corruption == "shape":
        raw["feedback_source"] = {"not": "a source"}
    elif corruption == "context":
        raw["feedback_source"]["context"]["idea"] = "Not the intent used for this feedback"
    elif corruption == "key":
        raw["feedback_source"]["content_key"] = "{}"
    elif corruption == "draft":
        raw["feedback_source"]["draft"]["logline"] = "Different source draft"
    elif corruption == "revision":
        raw["feedback_source"]["revision"] = project["revision"] + 100
    else:
        raw["feedback_source"][f"{corruption}_id"] = "different"
    stored = store.save(raw, project["revision"])
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert reopened["feedback_source"] is None
    assert reopened["feedback"] == project["feedback"]
    assert reopened["draft"] == project["draft"]
    assert reopened["author_context"] == project["author_context"]
    if corruption == "missing":
        assert all(version["feedback_source"] is None for version in reopened["versions"])
    assert store.get(project["id"]) == stored


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


def test_stream_reports_actual_steps_and_returns_saved_project(project_client, monkeypatch):
    client, provider = project_client
    stages = []
    original = provider.request_structured

    def record(request):
        stages.append(request.stage)
        return original(request)

    monkeypatch.setattr(provider, "request_structured", record)
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    response = client.post(f"{url}/analyze/stream", json={"revision": project["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert [(event["stage"], event["status"]) for event in events[:-1]] == [
        ("reasoning", "active"), ("reasoning", "completed"),
        ("saving", "active"), ("saving", "completed"),
    ]
    project = events[-1]["project"]
    assert events[-1]["type"] == "result"
    assert client.get(url).json() == project
    data = payload(project)
    data["answers"] = ["She leaves tomorrow", "He wants to apologize, not stop her"]
    project = client.put(url, json=data).json()
    response = client.post(f"{url}/plan/stream", json={"revision": project["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert stages[1:] == ["planning", "evaluation"]
    expected = [(stage, status) for stage in ("plan_choices", "planning_context", "planning", "planning_structure", "plan_checkpoint", "evaluation", "plan_save")
                for status in ("active", "completed")]
    assert [(event["stage"], event["status"]) for event in events[:-1]] == expected
    assert events[-1]["project"]["draft"] is not None
    assert provider.requests[1].stage == "planning"



def test_stream_returns_validation_error_without_model_call(project_client):
    client, provider = project_client
    project = start_project(client)
    response = client.post(f"/api/projects/{project['id']}/plan/stream",
                           json={"revision": project["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert [(e.get("stage"), e.get("status")) for e in events[:-1]] == [("plan_choices", "active"), ("plan_choices", "failed")]
    assert events[-1]["type"] == "error"
    assert provider.requests == []


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
    assert provider.requests[-1].response_model.__name__ == "_RevisionReviewOutput"
    assert "EDITED_ENDING" in provider.requests[-1].input_text
    assert "He wants to apologize" in provider.requests[-1].input_text
    assert "Only one apartment" in provider.requests[-1].input_text
    review_input = provider.requests[-1].input_text
    context = critic_author(provider.requests[-1])
    assert context["clarifications"] == [
        {"question": question, "answer": answer}
        for question, answer in zip(project["analysis"]["missing_information"], project["answers"])
    ]
    cards = json.loads(review_input.split("Card review context (JSON data):\n", 1)[1])["cards"]
    assert any(card["text"] == edited_draft["sections"][5]["content"] for card in cards)
    assert all(card["text"] in section["content"] for card in cards
               for section in edited_draft["sections"] if section["title"] == card["section"])
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


@pytest.mark.parametrize(
    ("idea", "policy"),
    [
        (
            "Một lab coach giúp học viên làm bài build phase tại VinUni; kết quả tuyển dụng để mở.",
            "Ngôn ngữ góp ý: tiếng Việt",
        ),
        (
            "A young tutor helps a learner finish an AI exercise. Her job result stays unknown.",
            "Use the explicit target response language for feedback",
        ),
    ],
)
def test_review_after_brief_and_draft_edits_keeps_terms_language_and_project_source(
    project_client, idea, policy
):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    original_draft = deepcopy(project["draft"])
    other = start_project(client)
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["idea"] = idea
    data["draft"]["title"] = "lab coach tại VinUni"
    data["draft"]["sections"][5]["content"] = (
        'BẢN ĐÃ SỬA: Lab coach tắt thư tuyển dụng, giúp học viên làm bài build phase. '
        'Dòng ghi chú là "Keep learning. / Cứ học tiếp."'
    )
    saved = client.put(url, json=data).json()
    assert saved["feedback_is_current"] is False
    response = client.post(f"{url}/review", json={"revision": saved["revision"]})
    assert response.status_code == 200, response.text
    reviewed = response.json()
    request = provider.requests[-1]
    assert policy in request.instructions
    cards = json.loads(request.input_text.split("Card review context (JSON data):\n", 1)[1])["cards"]
    assert any(card["text"] == saved["draft"]["title"] for card in cards)
    for card in cards:
        assert any(card["text"] in text for text in [saved["draft"]["title"], saved["draft"]["logline"],
                   *(section["content"] for section in saved["draft"]["sections"])])
    assert "He gives Linh his blessing at the airport curb." not in request.input_text
    assert reviewed["draft"] == saved["draft"]
    assert reviewed["feedback_is_current"] is True
    assert reviewed["feedback"]["artifact_id"] != project["feedback"]["artifact_id"]
    assert any(version["draft"] == original_draft for version in reviewed["versions"])
    assert client.get(url).json() == reviewed
    assert client.get(f"/api/projects/{other['id']}").json() == other


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
        if request.stage == "evaluation":
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


@pytest.mark.parametrize("new_questions", [[], ["Which final image do you want?"]])
def test_reanalysis_keeps_author_choices_for_planning_and_edited_review(
    project_client, monkeypatch, new_questions
):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    choices = [
        {"question": question, "answer": answer}
        for question, answer in zip(project["analysis"]["missing_information"], project["answers"])
    ]
    original_request = provider.request_structured

    def change_questions(request):
        result = original_request(request)
        if request.response_model.__name__ == "_ReasoningOutput":
            result.output.missing_information = new_questions
        return result

    monkeypatch.setattr(provider, "request_structured", change_questions)
    response = client.post(f"{url}/analyze", json={"revision": project["revision"]})
    assert response.status_code == 200
    project = response.json()
    brief = json.loads(provider.requests[-1].input_text.split("Creator brief (JSON data):\n", 1)[1])
    assert brief["clarifications"] == choices
    assert project["analysis"]["missing_information"] == new_questions
    card = project["author_context"]
    assert [(item["question"], item["answer"]) for item in card["clarifications"]] == [
        (item["question"], item["answer"]) for item in choices
    ]
    assert all(item["input_index"] is None for item in card["clarifications"])
    assert [item["question"] for item in card["pending_questions"]] == new_questions
    assert client.get(url).json() == project
    if new_questions:
        assert client.post(f"{url}/plan", json={"revision": project["revision"]}).status_code == 422
    data = payload(project)
    data["answers"] = ["An unopened letter remains on the table."] * len(new_questions)
    data["draft"]["sections"][5]["content"] = "EDITED: An unopened letter remains on the table."
    project = client.put(url, json=data).json()
    edited_draft = deepcopy(project["draft"])
    choices += [
        {"question": question, "answer": answer}
        for question, answer in zip(new_questions, project["answers"])
    ]
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 200
    project = response.json()
    context = critic_author(provider.requests[-1])
    assert context["clarifications"] == choices
    assert "EDITED: An unopened letter" in provider.requests[-1].input_text
    assert project["draft"] == edited_draft
    assert project["feedback_is_current"] is True
    assert project["feedback_source"]["context"] == project["author_context"]
    assert project["feedback_source"]["draft"] == edited_draft
    assert project["feedback_source"]["artifact_id"] == project["feedback"]["artifact_id"]
    response = client.post(f"{url}/plan", json={"revision": project["revision"]})
    assert response.status_code == 200
    for request in provider.requests[-2:]:
        context = critic_author(request)
        assert context["clarifications"] == choices
    project = response.json()
    data = payload(project)
    data["idea"] = "Một người mẹ đợi con trai trong căn bếp."
    changed = client.put(url, json=data).json()
    assert changed["clarifications"] == {}
    assert changed["feedback_is_current"] is False
    assert changed["clarification_history"][-1]["clarifications"] == {
        item["question"]: item["answer"] for item in choices
    }
    response = client.post(f"{url}/analyze", json={"revision": changed["revision"]})
    assert response.status_code == 200
    brief = json.loads(provider.requests[-1].input_text.split("Creator brief (JSON data):\n", 1)[1])
    assert brief["clarifications"] == []


def test_changed_or_cleared_answer_overrides_retained_choice(project_client):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    project = client.post(f"{url}/analyze", json={"revision": project["revision"]}).json()
    assert project["clarifications"]
    data = payload(project)
    data["answers"] = ["", "Chưa quyết định. Nếu đề xuất, ghi rõ đó là gợi ý của AI."]
    project = client.put(url, json=data).json()
    assert project["feedback_is_current"] is False
    assert client.post(f"{url}/plan", json={"revision": project["revision"]}).status_code == 422
    card = project["author_context"]
    assert [item["answer"] for item in card["clarifications"]] == [data["answers"][1]]
    assert card["clarifications"][0]["input_index"] == 1
    assert card["pending_questions"] == [{
        "question": project["analysis"]["missing_information"][0], "input_index": 0,
    }]
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 200
    context = critic_author(provider.requests[-1])
    assert context["clarifications"] == [
        {
            "question": project["analysis"]["missing_information"][1],
            "answer": data["answers"][1],
        }
    ]
    assert "He wants to apologize, not stop her" not in provider.requests[-1].input_text


def test_clear_initial_brief_waits_for_explicit_plan_request(project_client, monkeypatch):
    client, provider = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    original_request = provider.request_structured

    def no_questions(request):
        result = original_request(request)
        if request.response_model.__name__ == "_ReasoningOutput":
            result.output.missing_information = []
        return result

    monkeypatch.setattr(provider, "request_structured", no_questions)
    response = client.post(f"{url}/analyze", json={"revision": project["revision"]})
    assert response.status_code == 200
    project = response.json()
    assert project["draft"] is None
    assert project["answers"] == []
    assert len(provider.requests) == 1
    assert client.post(f"{url}/plan", json={"revision": project["revision"]}).status_code == 200
    assert len(provider.requests) == 3


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
    legacy.pop("clarifications", None)
    for version in legacy["versions"]:
        version.pop("questions", None)
        version.pop("clarifications", None)
    old_content = json.loads(legacy["reviewed_content"])
    old_content.pop("questions", None)
    old_content.pop("clarifications", None)
    legacy["reviewed_content"] = json.dumps(old_content, ensure_ascii=False, sort_keys=True)
    stored = store.save(legacy, project["revision"])
    response = client.get(f"/api/projects/{project['id']}")
    assert response.status_code == 200
    reopened = response.json()
    assert reopened["draft"] == project["draft"]
    assert reopened["feedback"] == project["feedback"]
    assert reopened["feedback_is_current"] is False
    assert reopened["clarification_history"] == []
    assert reopened["clarifications"] == {}
    assert reopened["versions"][0]["questions"] == []
    assert store.get(project["id"]) == stored


def test_unknown_language_is_saved_but_requires_selection_before_ai(project_client):
    client, provider = project_client
    project = client.post("/api/projects").json()
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["idea"] = "Une étudiante apprend à faire confiance à son équipe."
    project = client.put(url, json=data).json()
    response = client.post(f"{url}/analyze", json={"revision": project["revision"]})
    assert response.status_code == 422
    assert "chọn ngôn ngữ" in response.json()["detail"]
    assert client.get(url).json() == project
    assert provider.requests == []
    data = payload(project)
    data["response_language"] = "vi"
    project = client.put(url, json=data).json()
    project = develop_project(client, project)
    for request in provider.requests:
        assert "Target response language: Vietnamese" in request.input_text
    assert project["response_language"] == "vi"


def test_language_change_preserves_buffer_answers_versions_and_legacy_clients(project_client):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["response_language"] = "en"
    data["title"] = "Tên đang sửa"
    data["draft"]["sections"][5]["content"] = 'Bản đang sửa: lab coach nói "Keep learning."'
    call_count = len(provider.requests)
    saved = client.put(url, json=data).json()
    assert len(provider.requests) == call_count
    assert saved["draft"] == data["draft"]
    assert saved["title"] == data["title"]
    assert saved["analysis"] == project["analysis"]
    assert saved["answers"] == project["answers"]
    assert saved["clarification_history"] == project["clarification_history"]
    assert saved["feedback"] == project["feedback"]
    assert saved["feedback_is_current"] is False
    assert saved["versions"][0]["response_language"] == "auto"
    assert client.get(url).json() == saved
    # An older client does not send this field; it must not reset the saved choice.
    legacy_payload = payload(saved)
    saved = client.put(url, json=legacy_payload).json()
    assert saved["response_language"] == "en"
    reviewed = client.post(f"{url}/review", json={"revision": saved["revision"]}).json()
    assert "Target response language: English" in provider.requests[-1].input_text
    assert reviewed["draft"] == data["draft"]
    assert reviewed["response_language"] == "en"
    assert reviewed["feedback_is_current"] is True
    assert reviewed["versions"][-1]["response_language"] == "en"


def test_legacy_auto_language_keeps_recorded_content_key_and_reopens_without_writes(project_client):
    client, _ = project_client
    project = develop_project(client, start_project(client))
    store = project_routes.get_project_store()
    legacy = store.get(project["id"])
    legacy.pop("response_language")
    for version in legacy["versions"]:
        version.pop("response_language")
    stored = store.save(legacy, project["revision"])
    reopened = client.get(f"/api/projects/{project['id']}").json()
    assert reopened["response_language"] == "auto"
    assert reopened["feedback_is_current"] is True
    assert reopened["draft"] == project["draft"]
    assert reopened["feedback"] == project["feedback"]
    assert store.get(project["id"]) == stored


def test_generate_language_selection_and_invalid_choices(project_client):
    client, provider = project_client
    response = client.post("/api/generate", json={"idea": "AI"})
    assert response.status_code == 422
    assert provider.requests == []
    response = client.post("/api/generate", json={"idea": "AI", "response_language": "en"})
    assert response.status_code == 200
    assert all("Target response language: English" in r.input_text for r in provider.requests)
    assert client.post("/api/generate", json={"idea": "AI", "response_language": "fr"}).status_code == 422


def test_stream_review_failure_preserves_saved_edits_and_previous_feedback(project_client, monkeypatch):
    client, provider = project_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    previous_feedback = project["feedback"]
    data = payload(project)
    data["draft"]["sections"][0]["content"] = "Bản mới: lab coach vẫn hướng dẫn học viên."
    data["response_language"] = "en"
    project = client.put(url, json=data).json()
    before = client.get(url).json()

    def fail(request):
        raise MissingProviderConfigurationError("Model unavailable")

    monkeypatch.setattr(provider, "request_structured", fail)
    response = client.post(f"{url}/review/stream", json={"revision": project["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]["type"] == "error"
    assert any(event.get("status") == "failed" for event in events)
    assert client.get(url).json() == before
    assert before["feedback"] == previous_feedback
    assert before["response_language"] == "en"
    assert before["draft"]["sections"][0]["content"] == data["draft"]["sections"][0]["content"]


def test_stream_revision_conflict_does_not_overwrite_newer_content(project_client):
    client, provider = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    data = payload(project)
    data["idea"] += " lab coach"
    latest = client.put(url, json=data).json()
    response = client.post(f"{url}/analyze/stream", json={"revision": project["revision"]})
    events = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert events[-1]["type"] == "error"
    assert client.get(url).json() == latest
    assert provider.requests == []


def test_stream_disconnect_finishes_saving_without_overwriting_newer_edits(project_client, monkeypatch):
    """A dropped stream must not cancel work or bypass optimistic revision checks."""
    import asyncio
    import threading

    from app.api.schemas.projects import RevisionRequest

    client, provider = project_client
    project = start_project(client)
    url = f"/api/projects/{project['id']}"
    original = provider.request_structured
    release = threading.Event()

    def delayed(request):
        assert release.wait(timeout=5)
        return original(request)

    monkeypatch.setattr(provider, "request_structured", delayed)

    async def disconnected(change_content):
        response = await project_routes.stream_project_operation(
            project["id"], "analyze", RevisionRequest(revision=project["revision"])
        )
        iterator = response.body_iterator
        first = json.loads(await anext(iterator))
        assert first["stage"] == "reasoning" and first["status"] == "active"
        if change_content:
            data = payload(project)
            data["idea"] += " Bản mới chưa gửi cho AI: lab coach."
            latest = client.put(url, json=data).json()
        else:
            latest = None
        release.set()
        await asyncio.wait_for(iterator.aclose(), timeout=5)
        return latest

    asyncio.run(disconnected(False))
    project = client.get(url).json()
    assert project["analysis"] is not None
    assert len(provider.requests) == 1
    release.clear()
    latest = asyncio.run(disconnected(True))
    assert client.get(url).json() == latest
    assert len(provider.requests) == 2
