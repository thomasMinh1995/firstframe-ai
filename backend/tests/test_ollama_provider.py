import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from app.application.ai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderRequestError,
    ProviderTimeoutError,
    StructuredRequest,
)
from app.infrastructure.ollama_provider import OllamaProvider, OllamaProviderConfig


class DemoResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str


def install_response(monkeypatch, payload, status=200):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(status, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr("app.infrastructure.ollama_provider.httpx.post", post)
    return calls


def structured_request():
    return StructuredRequest(
        instructions="Preserve the creator's open ending. Respond in Vietnamese.",
        input_text='{"idea":"Mẹ chờ con", "clarifications":[{"answer":"Không hòa giải"}]}',
        response_model=DemoResponse,
    )


def test_local_request_preserves_context_and_enforces_schema(monkeypatch):
    calls = install_response(
        monkeypatch,
        {
            "done": True,
            "done_reason": "stop",
            "message": {"content": '{"title":"Chờ"}'},
        },
    )
    provider = OllamaProvider(OllamaProviderConfig(model="local-test"))
    request = structured_request()
    result = provider.request_structured(request)
    assert result.output == DemoResponse(title="Chờ")
    assert result.model == "local-test"
    url, kwargs = calls[0]
    body = kwargs["json"]
    assert url == "http://127.0.0.1:11434/api/chat"
    assert body["model"] == "local-test"
    assert body["format"] == DemoResponse.model_json_schema()
    assert body["stream"] is False
    assert body["messages"][0]["role"] == "system"
    assert request.instructions in body["messages"][0]["content"]
    assert body["messages"][1] == {"role": "user", "content": request.input_text}
    assert kwargs["trust_env"] is False
    assert kwargs["timeout"] == 180
    assert body["options"]["num_ctx"] == 16384


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"error": "internal error"},
        {"done": False, "message": {"content": '{"title":"Partial"}'}},
        {"done": True, "done_reason": "length", "message": {"content": '{"title":"Cut"}'}},
        {"done": True, "message": None},
        {"done": True, "message": {"content": ""}},
        {"done": True, "message": {"content": "not-json"}},
        {"done": True, "message": {"content": '{"name":"Wrong field"}'}},
    ],
)
def test_rejects_invalid_or_incomplete_output(monkeypatch, payload):
    install_response(monkeypatch, payload)
    with pytest.raises(MalformedProviderResponseError):
        OllamaProvider(OllamaProviderConfig(model="local-test")).request_structured(
            structured_request()
        )


def test_rejects_invalid_http_json(monkeypatch):
    monkeypatch.setattr(
        "app.infrastructure.ollama_provider.httpx.post",
        lambda *args, **kwargs: httpx.Response(
            200, text="not-json", request=httpx.Request("POST", args[0])
        ),
    )
    with pytest.raises(MalformedProviderResponseError):
        OllamaProvider(OllamaProviderConfig(model="local-test")).request_structured(
            structured_request()
        )


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (404, MissingProviderConfigurationError),
        (400, ProviderRequestError),
        (500, ProviderRequestError),
    ],
)
def test_maps_http_errors(monkeypatch, status, expected_error):
    install_response(monkeypatch, {"error": "private details"}, status)
    with pytest.raises(expected_error):
        OllamaProvider(OllamaProviderConfig(model="local-test")).request_structured(
            structured_request()
        )


@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        (httpx.ReadTimeout("slow"), ProviderTimeoutError),
        (httpx.ConnectError("offline"), ProviderRequestError),
    ],
)
def test_maps_transport_errors(monkeypatch, error, expected_error):
    def post(*args, **kwargs):
        raise error

    monkeypatch.setattr("app.infrastructure.ollama_provider.httpx.post", post)
    with pytest.raises(expected_error):
        OllamaProvider(OllamaProviderConfig(model="local-test")).request_structured(
            structured_request()
        )


def test_project_workflow_uses_local_fallback_and_preserves_edits(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from test_generate_workflow import FakeProvider

    from app.api.routes import projects as routes
    from app.application.project_store import ProjectStore
    from app.application.workflow import (
        _GroundedEvaluationOutput,
        _PlanningOutput,
        _ReasoningOutput,
    )
    from app.main import create_app

    monkeypatch.setenv("AI_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OLLAMA_MODEL", "local-test")
    monkeypatch.setattr(
        routes, "get_project_store", lambda: ProjectStore(tmp_path / "data.sqlite3")
    )
    fake = FakeProvider()
    models = {
        model.__name__: model for model in (_ReasoningOutput, _PlanningOutput, _GroundedEvaluationOutput)
    }

    def post(url, **kwargs):
        body = kwargs["json"]
        assert body["model"] == "local-test"
        result = fake.request_structured(
            StructuredRequest(
                instructions=body["messages"][0]["content"],
                input_text=body["messages"][1]["content"],
                response_model=models[body["format"]["title"]],
            )
        )
        return httpx.Response(
            200,
            json={
                "done": True,
                "message": {"content": result.output.model_dump_json()},
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.infrastructure.ollama_provider.httpx.post", post)
    client = TestClient(create_app())
    project = client.post("/api/projects", json={"title": "Local brainstorm"}).json()
    url = f"/api/projects/{project['id']}"

    def save(**changes):
        body = {
            key: project[key]
            for key in ("revision", "title", "idea", "constraints", "answers", "draft")
        }
        body.update(changes)
        response = client.put(url, json=body)
        assert response.status_code == 200
        return response.json()

    def action(name):
        response = client.post(f"{url}/{name}", json={"revision": project["revision"]})
        assert response.status_code == 200, response.text
        return response.json()

    project = save(idea="A father wants to apologize.", constraints=["Only one apartment."])
    project = action("analyze")
    project = save(answers=["He wants to apologize, not stop her.", "Keep the ending open."])
    project = action("plan")
    project["draft"]["sections"][-1]["content"] = "EDITED: An unopened letter."
    project = save()
    draft = project["draft"]
    project = action("review")
    assert project["draft"] == draft
    assert project["feedback_is_current"] is True
    for request in fake.requests[1:]:
        assert "not stop her" in request.input_text
        assert "Only one apartment" in request.input_text
    assert "EDITED: An unopened letter" in fake.requests[-1].input_text

    def offline(*args, **kwargs):
        raise httpx.ConnectError("private diagnostic")

    monkeypatch.setattr("app.infrastructure.ollama_provider.httpx.post", offline)
    response = client.post(f"{url}/review", json={"revision": project["revision"]})
    assert response.status_code == 502
    assert "private diagnostic" not in response.text
    assert client.get(url).json() == project
