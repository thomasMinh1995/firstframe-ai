import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from test_generate_workflow import FakeProvider
from test_projects import develop_project, payload, start_project

from app.api.routes import projects as routes
from app.application.ai_provider import ProviderTimeoutError, StructuredRequest
from app.application.dataset import DatasetStore, capture_workflow, recording_provider
from app.application.project_store import ProjectStore
from app.application.workflow import _EvaluationOutput, _PlanningOutput, _ReasoningOutput
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig
from app.infrastructure.openai_provider import OpenAIProvider, OpenAIProviderConfig
from app.main import create_app


@pytest.fixture
def dataset_client(tmp_path, monkeypatch):
    project_store = ProjectStore(tmp_path / "projects.sqlite3")
    monkeypatch.setattr(routes, "get_project_store", lambda: project_store)
    provider = FakeProvider()
    monkeypatch.setattr("app.application.workflow.create_provider", lambda: provider)
    return TestClient(create_app()), provider


def exported(store):
    return sorted(
        (json.loads(path.read_text()) for path in (store.directory / "runs").glob("*.json")),
        key=lambda record: record["started_at"],
    )


@pytest.mark.parametrize("backend", ["openai", "ollama"])
def test_records_real_adapter_identity_and_actual_model(
    backend, monkeypatch, local_dataset_directory
):
    fake = FakeProvider()
    models = [_ReasoningOutput, _PlanningOutput, _EvaluationOutput]
    actual_model = "gpt-resolved-snapshot" if backend == "openai" else "qwen-local:latest"
    monkeypatch.setenv("AI_PROVIDER", "misleading-env-value")
    if backend == "openai":
        model_iterator = iter(models)

        def create(**kwargs):
            output = fake.request_structured(
                StructuredRequest(kwargs["instructions"], kwargs["input"], next(model_iterator))
            ).output
            return SimpleNamespace(
                id="response-test", model=actual_model, output_text=output.model_dump_json()
            )

        provider = OpenAIProvider(
            OpenAIProviderConfig("secret-api-key-not-for-export", "requested-alias", 0.3),
            client=SimpleNamespace(responses=SimpleNamespace(create=create)),
        )
    else:
        by_title = {model.__name__: model for model in models}

        def post(url, **kwargs):
            body = kwargs["json"]
            output = fake.request_structured(
                StructuredRequest(
                    body["messages"][0]["content"],
                    body["messages"][1]["content"],
                    by_title[body["format"]["title"]],
                )
            ).output
            return httpx.Response(
                200,
                json={
                    "done": True,
                    "model": actual_model,
                    "message": {"content": output.model_dump_json()},
                },
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr("app.infrastructure.ollama_provider.httpx.post", post)
        provider = OllamaProvider(OllamaProviderConfig("requested-alias"))

    monkeypatch.setattr("app.application.workflow.create_provider", lambda: provider)
    response = TestClient(create_app()).post(
        "/api/generate",
        json={
            "idea": "Một người cha muốn xin lỗi con gái.",
            "constraints": ["Chỉ một căn hộ"],
        },
    )
    assert response.status_code == 200, response.text
    store = DatasetStore(local_dataset_directory)
    (record,) = store.records()
    assert exported(store) == [record]
    assert record["status"] == "completed"
    assert record["workflow_complete"] is True
    assert record["review_status"] == "unreviewed" and record["human_feedback"] is None
    assert record["models_used"] == [{"provider": backend, "model": actual_model}]
    assert record["output"] == response.json()
    assert [step["stage"] for step in record["steps"]] == ["reasoning", "planning", "evaluation"]
    for step in record["steps"]:
        assert step["provider"] == backend
        assert step["requested_model"] == "requested-alias"
        assert step["model"] == actual_model
        assert step["parameters"]["temperature"] == 0.3
        assert step["duration_ms"] >= 0
        assert json.loads(step["raw_output"]) == step["output"]
        assert step["request"]["response_schema"]
        assert len(step["request"]["prompt_sha256"]) == 64
    assert "Short-film domain knowledge" in record["steps"][1]["request"]["input_text"]
    assert "Short-film story rubric" in record["steps"][2]["request"]["input_text"]
    serialized = json.dumps(record, ensure_ascii=False)
    assert "secret-api-key-not-for-export" not in serialized
    assert "misleading-env-value" not in serialized


def test_project_exports_linked_rounds_and_exact_edited_draft(
    dataset_client, local_dataset_directory
):
    client, _ = dataset_client
    project = develop_project(client, start_project(client))
    store = DatasetStore(local_dataset_directory)
    analyze, plan = store.records()
    assert analyze["operation"] == "analyze"
    assert analyze["workflow_complete"] is False
    assert plan["operation"] == "plan" and plan["workflow_complete"] is True
    assert plan["parent_run_id"] == analyze["run_id"]
    assert plan["source_analysis_id"] == project["analysis"]["artifact_id"]
    assert plan["output_revision"] == project["revision"]
    assert plan["input_revision"] + 1 == plan["output_revision"]
    assert plan["input"]["answers"] == project["answers"]
    assert [step["stage"] for step in plan["steps"]] == ["planning", "evaluation"]
    assert "versions" not in plan["output"]
    data = payload(project)
    data["draft"]["sections"][-1]["content"] = "EDITED: Mẹ đặt chiếc thìa xuống."
    url = f"/api/projects/{project['id']}"
    project = client.put(url, json=data).json()
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 200
    review = store.records()[-1]
    assert review["parent_run_id"] == plan["run_id"]
    assert review["input"]["draft"] == data["draft"] == review["output"]["draft"]
    assert "Mẹ đặt chiếc thìa" in review["steps"][0]["request"]["input_text"]
    assert review["output"]["feedback_is_current"] is True
    assert exported(store) == store.records()


def test_failed_critic_keeps_successful_planning_but_does_not_export_as_complete(
    dataset_client, monkeypatch, local_dataset_directory
):
    client, provider = dataset_client
    project = develop_project(client, start_project(client))
    original = provider.request_structured

    def timeout(request):
        if request.stage == "evaluation":
            raise ProviderTimeoutError("secret diagnostic")
        return original(request)

    monkeypatch.setattr(provider, "request_structured", timeout)
    url = f"/api/projects/{project['id']}"
    response = client.post(f"{url}/plan", json={"revision": project["revision"]})
    assert response.status_code == 504
    record = DatasetStore(local_dataset_directory).records()[-1]
    assert record["status"] == "failed" and record["workflow_complete"] is False
    assert record["output"] is None
    assert [step["status"] for step in record["steps"]] == ["completed", "failed"]
    assert record["steps"][0]["output"]["story_plan"]
    assert record["steps"][1]["error_type"] == "ProviderTimeoutError"
    assert "secret diagnostic" not in json.dumps(record)
    assert client.get(url).json() == project
    assert exported(DatasetStore(local_dataset_directory))[-1] == record


def test_revision_conflict_is_not_a_completed_sample(
    dataset_client, monkeypatch, local_dataset_directory
):
    client, provider = dataset_client
    project = develop_project(client, start_project(client))
    original = provider.request_structured

    def concurrent_edit(request):
        result = original(request)
        store = routes.get_project_store()
        newer = store.get(project["id"])
        newer["title"] = "Saved in another window"
        store.save(newer, newer["revision"])
        return result

    monkeypatch.setattr(provider, "request_structured", concurrent_edit)
    url = f"/api/projects/{project['id']}"
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 409
    record = DatasetStore(local_dataset_directory).records()[-1]
    assert record["status"] == "conflict" and record["output"] is None
    assert record["steps"][0]["status"] == "completed"
    assert client.get(url).json()["title"] == "Saved in another window"


def test_failed_file_export_can_be_recovered_without_rerunning_ai(
    dataset_client, monkeypatch, local_dataset_directory
):
    client, _ = dataset_client

    def disk_error(self, record):
        raise OSError("disk unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(DatasetStore, "export_run", disk_error)
        response = client.post("/api/generate", json={"idea": "A father says goodbye."})
    assert response.status_code == 200
    store = DatasetStore(local_dataset_directory)
    (record,) = store.records()
    assert record["status"] == "completed" and exported(store) == []
    destination = local_dataset_directory / "all.jsonl"
    assert store.export(destination) == 1
    assert exported(store) == [record]
    with pytest.raises(ValueError, match="must not overwrite"):
        store.export(store.database)
    assert store.records() == [record]
    assert [json.loads(line) for line in destination.read_text().splitlines()] == [record]
    assert store.export(destination) == 1
    assert exported(store) == [record]
    result = subprocess.run(
        [sys.executable, "-m", "app.application.dataset", "--output", str(destination)],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Exported 1 workflow records" in result.stdout


def test_recorder_failure_does_not_break_generation(dataset_client, monkeypatch, caplog):
    client, _ = dataset_client

    def disk_error(self, record):
        raise OSError("disk unavailable")

    monkeypatch.setattr(DatasetStore, "save", disk_error)
    response = client.post("/api/generate", json={"idea": "A father says goodbye."})
    assert response.status_code == 200
    assert "Dataset write failed" in caplog.text


def test_invalid_model_output_is_preserved_as_a_failed_sample(monkeypatch, local_dataset_directory):
    monkeypatch.setattr(
        "app.infrastructure.ollama_provider.httpx.post",
        lambda url, **kwargs: httpx.Response(
            200,
            json={
                "done": True,
                "message": {"content": "not valid JSON"},
            },
            request=httpx.Request("POST", url),
        ),
    )
    monkeypatch.setattr(
        "app.application.workflow.create_provider",
        lambda: OllamaProvider(OllamaProviderConfig("local-test")),
    )
    response = TestClient(create_app()).post("/api/generate", json={"idea": "A quiet kitchen."})
    assert response.status_code == 502
    (record,) = DatasetStore(local_dataset_directory).records()
    assert record["status"] == "failed" and record["workflow_complete"] is False
    (step,) = record["steps"]
    assert step["provider"] == "ollama" and step["requested_model"] == "local-test"
    assert step["raw_output"] == "not valid JSON"
    assert step["output"] is None
    assert step["error_type"] == "MalformedProviderResponseError"


def test_new_brief_starts_a_separate_dataset_chain(dataset_client, local_dataset_directory):
    client, _ = dataset_client
    project = develop_project(client, start_project(client))
    url = f"/api/projects/{project['id']}"
    body = payload(project)
    body["idea"] = "A different story about a mother waiting at home."
    project = client.put(url, json=body).json()
    response = client.post(f"{url}/analyze", json={"revision": project["revision"]})
    assert response.status_code == 200
    record = DatasetStore(local_dataset_directory).records()[-1]
    assert record["parent_run_id"] is None and record["source_analysis_id"] is None
    assert record["input"]["clarifications"] == {}
    assert record["input"]["answers"] == []


def test_concurrent_runs_do_not_mix_context_or_outputs(local_dataset_directory):
    class Output(BaseModel):
        title: str

    barrier = Barrier(2)

    def worker(idea):
        provider = FakeProvider()
        with capture_workflow("analyze", {"idea": idea}) as run:
            wrapped = recording_provider(provider)
            barrier.wait(timeout=10)
            # A small provider with the same contract makes interleaving observable.
            provider.request_structured = lambda request: SimpleNamespace(
                output=Output(title=request.input_text),
                model="thread-model",
                response_id=None,
                raw_output=None,
            )
            result = wrapped.request_structured(
                StructuredRequest("Mentor", idea, Output, stage="reasoning")
            )
            run.complete(result.output.model_dump())
        assert recording_provider(provider) is provider

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, ["First story", "Second story"]))
    records = DatasetStore(local_dataset_directory).records()
    assert len(records) == 2
    for record in records:
        assert record["input"]["idea"] == record["output"]["title"]
        assert record["steps"][0]["request"]["input_text"] == record["input"]["idea"]
