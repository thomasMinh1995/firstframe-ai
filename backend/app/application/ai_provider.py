import json
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel


class ProviderError(Exception):
    """Base class for provider-independent failures."""


class MissingProviderConfigurationError(ProviderError):
    """Required provider configuration or a local model is missing."""


class ProviderTimeoutError(ProviderError):
    """The provider request timed out."""


class ProviderRequestError(ProviderError):
    """The provider request failed."""


class MalformedProviderResponseError(ProviderError):
    """The provider did not return the requested structured shape."""

    def __init__(self, message: str, *, raw_output: str | None = None) -> None:
        super().__init__(message)
        self.raw_output = raw_output


@dataclass(frozen=True)
class ProviderMetadata:
    provider: str
    model: str
    parameters: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class StructuredRequest:
    instructions: str
    input_text: str
    response_model: type[BaseModel]
    stage: str = ""
    timeout_seconds: float | None = None


@dataclass(frozen=True)
class StructuredResult:
    output: BaseModel
    model: str
    response_id: str | None = None
    raw_output: str | None = None


class StructuredProvider(Protocol):
    @property
    def metadata(self) -> ProviderMetadata: ...

    def request_structured(self, request: StructuredRequest) -> StructuredResult: ...


def strict_json_instructions(request: StructuredRequest) -> str:
    return (
        f"{request.instructions}\n\n"
        "Return strict JSON only. Do not wrap the response in markdown. Do not include "
        "explanatory text before or after the JSON. The JSON must conform to this schema:\n"
        f"{json.dumps(request.response_model.model_json_schema(), ensure_ascii=False)}"
    )
