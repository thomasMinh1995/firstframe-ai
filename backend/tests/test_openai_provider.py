from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError
from pydantic import BaseModel

from app.infrastructure.openai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    OpenAIProvider,
    OpenAIProviderConfig,
    OpenAIStructuredRequest,
    ProviderRequestError,
    ProviderTimeoutError,
)


class DemoResponse(BaseModel):
    title: str


class FakeResponses:
    def __init__(self, result: object | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses) -> None:
        self.responses = responses


def test_provider_sends_structured_request_and_parses_valid_json_output() -> None:
    responses = FakeResponses(
        result=SimpleNamespace(id="response-1", output_text='{"title":"A quiet goodbye"}')
    )
    provider = OpenAIProvider(
        config=OpenAIProviderConfig(api_key="test-key", model="gpt-test", temperature=0.3),
        client=FakeOpenAIClient(responses),  # type: ignore[arg-type]
    )

    result = provider.request_structured(
        OpenAIStructuredRequest(
            instructions="Return a structured response.",
            input_text="A seed idea.",
            response_model=DemoResponse,
        )
    )

    assert result.output == DemoResponse(title="A quiet goodbye")
    assert result.model == "gpt-test"
    assert result.response_id == "response-1"
    assert responses.calls[0]["model"] == "gpt-test"
    assert responses.calls[0]["input"] == "A seed idea."
    assert responses.calls[0]["temperature"] == 0.3
    assert "Return strict JSON only" in str(responses.calls[0]["instructions"])


def test_provider_fails_when_api_key_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(MissingProviderConfigurationError):
        OpenAIProvider.from_env()


def test_provider_maps_timeout_to_provider_error() -> None:
    responses = FakeResponses(error=APITimeoutError(request=None))
    provider = OpenAIProvider(
        config=OpenAIProviderConfig(api_key="test-key", model="gpt-test", temperature=0.3),
        client=FakeOpenAIClient(responses),  # type: ignore[arg-type]
    )

    with pytest.raises(ProviderTimeoutError):
        provider.request_structured(
            OpenAIStructuredRequest(
                instructions="Return a structured response.",
                input_text="A seed idea.",
                response_model=DemoResponse,
            )
        )


def test_provider_maps_openai_exception_to_provider_error() -> None:
    responses = FakeResponses(
        error=APIConnectionError(request=httpx.Request("POST", "https://api.openai.com"))
    )
    provider = OpenAIProvider(
        config=OpenAIProviderConfig(api_key="test-key", model="gpt-test", temperature=0.3),
        client=FakeOpenAIClient(responses),  # type: ignore[arg-type]
    )

    with pytest.raises(ProviderRequestError):
        provider.request_structured(
            OpenAIStructuredRequest(
                instructions="Return a structured response.",
                input_text="A seed idea.",
                response_model=DemoResponse,
            )
        )


def test_provider_rejects_invalid_json_output() -> None:
    responses = FakeResponses(result=SimpleNamespace(id="response-1", output_text="not-json"))
    provider = OpenAIProvider(
        config=OpenAIProviderConfig(api_key="test-key", model="gpt-test", temperature=0.3),
        client=FakeOpenAIClient(responses),  # type: ignore[arg-type]
    )

    with pytest.raises(MalformedProviderResponseError):
        provider.request_structured(
            OpenAIStructuredRequest(
                instructions="Return a structured response.",
                input_text="A seed idea.",
                response_model=DemoResponse,
            )
        )


def test_provider_rejects_json_that_does_not_match_schema() -> None:
    responses = FakeResponses(result=SimpleNamespace(id="response-1", output_text='{"name":"Nope"}'))
    provider = OpenAIProvider(
        config=OpenAIProviderConfig(api_key="test-key", model="gpt-test", temperature=0.3),
        client=FakeOpenAIClient(responses),  # type: ignore[arg-type]
    )

    with pytest.raises(MalformedProviderResponseError):
        provider.request_structured(
            OpenAIStructuredRequest(
                instructions="Return a structured response.",
                input_text="A seed idea.",
                response_model=DemoResponse,
            )
        )
