import hashlib
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_generate_workflow import FakeProvider
from test_projects import develop_project, payload, start_project

from app.api.routes import projects as routes
from app.api.schemas.projects import ProjectResponse
from app.application.dataset import DatasetStore
from app.application.project_store import ProjectStore
from app.infrastructure.ollama_provider import OllamaProvider
from app.infrastructure.openai_provider import OpenAIProvider
from app.main import create_app


@pytest.fixture
def demo_exports(tmp_path, monkeypatch, local_dataset_directory):
    monkeypatch.setenv("DEMO_DATASET_DIR", str(local_dataset_directory))
    store = ProjectStore(tmp_path / "projects.sqlite3")
    monkeypatch.setattr(routes, "get_project_store", lambda: store)
    monkeypatch.setattr("app.application.workflow.create_provider", lambda: FakeProvider())
    client = TestClient(create_app())
    project = develop_project(client, start_project(client))
    return client, project, DatasetStore(local_dataset_directory)


def add_review(client, project):
    url = f"/api/projects/{project['id']}"
    body = payload(project)
    body["draft"]["sections"][-1]["content"] = "EDITED: Một lá thư chưa mở trên bàn."
    project = client.put(url, json=body).json()
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 200
    return response.json()


def prohibit_live_work(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Demo must not invoke AI or write projects/datasets")

    monkeypatch.setattr("app.application.workflow.create_provider", forbidden)
    monkeypatch.setattr(OpenAIProvider, "request_structured", forbidden)
    monkeypatch.setattr(OllamaProvider, "request_structured", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)
    monkeypatch.setattr(DatasetStore, "save", forbidden)
    monkeypatch.setattr(DatasetStore, "export_run", forbidden)
    monkeypatch.setattr(ProjectStore, "save", forbidden)
    monkeypatch.setattr(ProjectStore, "create", forbidden)


def files_digest(directory):
    return {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*")
        if path.is_file()
    }


def test_replays_exported_rounds_without_ai_or_mutating_data(demo_exports, monkeypatch):
    client, project, store = demo_exports
    reviewed = add_review(client, project)
    original_files = files_digest(store.directory)
    prohibit_live_work(monkeypatch)
    response = client.get("/api/demo/scenarios")
    assert response.status_code == 200
    (summary,) = response.json()
    assert "steps" not in summary
    assert summary["step_count"] == 7
    assert summary["review_status"] == "unreviewed"
    assert summary["models_used"] == [{"provider": "fake", "model": "fake-model"}]
    detail = client.get(f"/api/demo/scenarios/{summary['id']}")
    assert detail.status_code == 200
    steps = detail.json()["steps"]
    assert [step["kind"] for step in steps] == [
        "brief",
        "analysis",
        "answers",
        "plan",
        "evaluation",
        "edit",
        "review",
    ]
    assert steps[0]["idea"] == project["idea"]
    assert steps[1]["analysis"] == project["analysis"]
    assert [answer["answer"] for answer in steps[2]["answers"]] == project["answers"]
    assert steps[3]["draft"] == project["draft"]
    assert steps[5]["draft"] == steps[6]["draft"] == reviewed["draft"]
    assert steps[6]["feedback"] == reviewed["feedback"]
    assert detail.json() == client.get(f"/api/demo/scenarios/{summary['id']}").json()
    assert files_digest(store.directory) == original_files


def test_jsonl_only_export_and_duplicate_json_records_are_supported(
    demo_exports, tmp_path, monkeypatch
):
    client, _, store = demo_exports
    records = store.records()
    portable = tmp_path / "portable"
    portable.mkdir()
    (portable / "recordings.jsonl").write_text(
        "not-json\n" + "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )
    # The same export in JSON and JSONL must not duplicate scenarios.
    (portable / "same-plan.json").write_text(json.dumps(records[-1]), encoding="utf-8")
    monkeypatch.setenv("DEMO_DATASET_DIR", str(portable))
    prohibit_live_work(monkeypatch)
    (summary,) = client.get("/api/demo/scenarios").json()
    scenario = client.get(f"/api/demo/scenarios/{summary['id']}").json()
    assert scenario["step_count"] == 5
    assert scenario["steps"][2]["answers"]


def test_missing_analysis_export_uses_saved_snapshot_without_inventing_provenance(demo_exports):
    client, project, store = demo_exports
    analysis, _ = store.records()
    (store.directory / "runs" / f"{analysis['run_id']}.json").unlink()
    (summary,) = client.get("/api/demo/scenarios").json()
    step = client.get(f"/api/demo/scenarios/{summary['id']}").json()["steps"][1]
    assert step["analysis"] == project["analysis"]
    assert step["models_used"] == [] and step["source_run_id"] is None


def test_separate_review_branches_are_selectable_without_mixing_drafts(demo_exports):
    client, project, store = demo_exports
    reviewed = add_review(client, project)
    records = store.records()
    variant = json.loads(json.dumps(records[-1]))
    variant["run_id"] = str(uuid4())
    variant["input"]["draft"]["sections"][-1]["content"] = "BRANCH: Chiếc chìa khóa cạnh cửa."
    after = ProjectResponse.model_validate(variant["output"])
    after.draft.sections[-1].content = "BRANCH: Chiếc chìa khóa cạnh cửa."
    after.reviewed_content = after.content_key()
    variant["output"] = after.model_dump(mode="json")
    store.export_run(variant)
    summaries = client.get("/api/demo/scenarios").json()
    assert len(summaries) == 2 and len({item["id"] for item in summaries}) == 2
    assert all("nhánh" in item["title"] for item in summaries)
    final_drafts = [
        client.get(f"/api/demo/scenarios/{item['id']}").json()["steps"][-1]["draft"]
        for item in summaries
    ]
    assert reviewed["draft"] in final_drafts
    assert after.draft.model_dump(mode="json") in final_drafts


def test_review_from_different_brief_cannot_join_scenario(demo_exports):
    client, project, store = demo_exports
    add_review(client, project)
    review = store.records()[-1]
    review["input"]["idea"] = "An unrelated story."
    after = ProjectResponse.model_validate(review["output"])
    after.idea = "An unrelated story."
    after.reviewed_content = after.content_key()
    review["output"] = after.model_dump(mode="json")
    store.export_run(review)
    (summary,) = client.get("/api/demo/scenarios").json()
    assert summary["step_count"] == 5


def test_legacy_full_generate_export_is_a_demo_scenario(demo_exports):
    client, _, _ = demo_exports
    response = client.post("/api/generate", json={"idea": "A completely new legacy story."})
    assert response.status_code == 200
    summaries = client.get("/api/demo/scenarios").json()
    legacy = next(item for item in summaries if "legacy story" in item["description"])
    steps = client.get(f"/api/demo/scenarios/{legacy['id']}").json()["steps"]
    assert len(steps) == 5
    assert steps[1]["analysis"] == response.json()["analysis"]
    assert steps[2]["answers"] == []
    assert "trực tiếp" in steps[2]["description"]
    assert steps[4]["feedback"] == response.json()["evaluation"]


def test_conflicting_ids_do_not_choose_an_arbitrary_story(demo_exports):
    client, _, store = demo_exports
    plan = store.records()[-1]
    plan["output"]["title"] = "Another story using the same recording ID"
    (store.directory / "duplicate.json").write_text(json.dumps(plan), encoding="utf-8")
    assert client.get("/api/demo/scenarios").json() == []


@pytest.mark.parametrize(
    "change",
    [
        {"status": "failed"},
        {"status": "running"},
        {"status": "conflict"},
        {"schema_version": 99},
        {"workflow_complete": False},
        {"output": {}},
        {"steps": []},
    ],
)
def test_incomplete_or_invalid_plan_is_not_offered(demo_exports, change):
    client, _, store = demo_exports
    plan = store.records()[-1]
    plan.update(change)
    store.export_run(plan)
    assert client.get("/api/demo/scenarios").json() == []


def test_empty_directory_and_missing_scenario_do_not_call_ai(tmp_path, monkeypatch):
    directory = tmp_path / "empty-demo"
    monkeypatch.setenv("DEMO_DATASET_DIR", str(directory))
    prohibit_live_work(monkeypatch)
    client = TestClient(create_app())
    assert client.get("/api/demo/scenarios").json() == []
    assert client.get("/api/demo/scenarios/not-found").status_code == 404
    assert not directory.exists()


def test_bundled_demo_is_a_real_export_with_preserved_model_metadata(monkeypatch):
    monkeypatch.delenv("DEMO_DATASET_DIR", raising=False)
    prohibit_live_work(monkeypatch)
    client = TestClient(create_app())
    (summary,) = client.get("/api/demo/scenarios").json()
    assert summary["models_used"] == [{"provider": "ollama", "model": "qwen2.5:3b"}]
    assert summary["review_status"] == "unreviewed"
    scenario = client.get(f"/api/demo/scenarios/{summary['id']}").json()
    assert scenario["steps"][2]["answers"] == []
    assert "chiếc thìa" in scenario["steps"][-1]["draft"]["sections"][5]["content"]
