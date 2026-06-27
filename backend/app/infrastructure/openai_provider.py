import logging
import os
import json
from dataclasses import dataclass
from json import JSONDecodeError
from typing import TypeVar

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, OpenAIError
from pydantic import BaseModel, ValidationError


logger = logging.getLogger(__name__)
StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)


class ProviderError(Exception):
    """Base class for provider-independent failures."""


class MissingProviderConfigurationError(ProviderError):
    """Raised when required provider configuration is missing."""


class ProviderTimeoutError(ProviderError):
    """Raised when the provider request times out."""


class ProviderRequestError(ProviderError):
    """Raised when the provider request fails."""


class MalformedProviderResponseError(ProviderError):
    """Raised when the provider does not return the requested structured shape."""


@dataclass(frozen=True)
class OpenAIProviderConfig:
    api_key: str
    model: str
    temperature: float
    timeout_seconds: float = 45.0


@dataclass(frozen=True)
class OpenAIStructuredRequest:
    instructions: str
    input_text: str
    response_model: type[StructuredResponseT]


@dataclass(frozen=True)
class OpenAIStructuredResult:
    output: BaseModel
    model: str
    response_id: str | None = None


class OpenAIProvider:
    """Thin OpenAI adapter for structured provider calls.

    This adapter owns OpenAI client interaction only. It does not know about the
    Harness workflow, domain plugins, prompts, or story-development business rules.
    """

    def __init__(self, config: OpenAIProviderConfig, client: OpenAI | None = None) -> None:
        self._config = config
        self._client = client or OpenAI(api_key=config.api_key, timeout=config.timeout_seconds)

    @classmethod
    def from_env(cls) -> "OpenAIProvider":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise MissingProviderConfigurationError("OPENAI_API_KEY is required.")

        model = os.getenv("MODEL", "gpt-5.5").strip() or "gpt-5.5"
        raw_temperature = os.getenv("TEMPERATURE", "0.3").strip() or "0.3"

        try:
            temperature = float(raw_temperature)
        except ValueError as error:
            raise MissingProviderConfigurationError("TEMPERATURE must be a number.") from error

        return cls(
            OpenAIProviderConfig(
                api_key=api_key,
                model=model,
                temperature=temperature,
            )
        )

    def request_structured(
        self, request: OpenAIStructuredRequest
    ) -> OpenAIStructuredResult:
        provider_method = "responses.create"
        logger.info(
            "Sending structured OpenAI request with model=%s method=%s",
            self._config.model,
            provider_method,
        )
        try:
            response = self._client.responses.create(
                model=self._config.model,
                instructions=_strict_json_instructions(request),
                input=request.input_text,
                temperature=self._config.temperature,
            )
        except APITimeoutError as error:
            _log_provider_exception(provider_method, self._config.model, error)
            raise ProviderTimeoutError("The AI provider timed out.") from error
        except APIConnectionError as error:
            _log_provider_exception(provider_method, self._config.model, error)
            raise ProviderRequestError("The AI provider could not be reached.") from error
        except (APIError, OpenAIError) as error:
            _log_provider_exception(provider_method, self._config.model, error)
            raise ProviderRequestError("The AI provider request failed.") from error

        raw_output = _extract_output_text(response)
        if raw_output is None:
            logger.warning(
                "OpenAI structured output missing text model=%s method=%s",
                self._config.model,
                provider_method,
            )
            raise MalformedProviderResponseError(
                "The AI provider returned an invalid structured response."
            )

        try:
            payload = json.loads(raw_output)
            parsed_output = request.response_model.model_validate(payload)
        except (JSONDecodeError, ValidationError, TypeError) as error:
            logger.warning(
                "OpenAI structured output validation failed model=%s method=%s "
                "exception_class=%s exception_message=%s raw_output_preview=%s",
                self._config.model,
                provider_method,
                error.__class__.__name__,
                str(error),
                _safe_preview(raw_output),
            )
            raise MalformedProviderResponseError(
                "The AI provider returned an invalid structured response."
            ) from error

        return OpenAIStructuredResult(
            output=parsed_output,
            model=self._config.model,
            response_id=getattr(response, "id", None),
        )


def _strict_json_instructions(request: OpenAIStructuredRequest) -> str:
    schema = request.response_model.model_json_schema()
    return (
        f"{request.instructions}\n\n"
        "Return strict JSON only. Do not wrap the response in markdown. Do not include "
        "explanatory text before or after the JSON. The JSON must conform to this schema:\n"
        f"{json.dumps(schema, ensure_ascii=False)}"
    )


def _extract_output_text(response: object) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None)
    if not isinstance(output, list):
        return None

    chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", None)
        if not isinstance(content, list):
            continue
        for content_item in content:
            text = getattr(content_item, "text", None)
            if isinstance(text, str):
                chunks.append(text)

    combined = "".join(chunks).strip()
    return combined or None


def _log_provider_exception(method: str, model: str, error: Exception) -> None:
    logger.warning(
        "OpenAI provider request failed model=%s method=%s exception_class=%s "
        "exception_message=%s",
        model,
        method,
        error.__class__.__name__,
        str(error),
    )


def _safe_preview(raw_output: str, limit: int = 500) -> str:
    compact = raw_output.replace("\n", "\\n")
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."
