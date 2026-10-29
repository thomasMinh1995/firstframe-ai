import logging
import math
import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

from app.application.ai_provider import (
    MalformedProviderResponseError,
    MissingProviderConfigurationError,
    ProviderMetadata,
    ProviderRequestError,
    ProviderTimeoutError,
    StructuredRequest,
    StructuredResult,
    strict_json_instructions,
)

from app.application.screenplay_context import SCREENPLAY_OUTPUT_TOKENS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaProviderConfig:
    model: str
    base_url: str = "http://127.0.0.1:11434"
    temperature: float = 0.3
    timeout_seconds: float = 180.0
    context_length: int = 16384


class OllamaProvider:
    """Run the same structured workflow against Ollama's native local API."""

    def __init__(self, config: OllamaProviderConfig) -> None:
        self._config = config

    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            "ollama",
            self._config.model,
            {
                "temperature": self._config.temperature,
                "timeout_seconds": self._config.timeout_seconds,
                "num_ctx": self._config.context_length,
            },
        )

    @classmethod
    def from_env(cls) -> "OllamaProvider":
        load_dotenv()
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip() or "qwen2.5:3b"
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/")
        try:
            url = httpx.URL(base_url)
            temperature = float(os.getenv("TEMPERATURE", "0.3"))
            timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
            context_length = int(os.getenv("OLLAMA_CONTEXT_LENGTH", "16384"))
            if (
                url.scheme not in {"http", "https"}
                or not url.host
                or not math.isfinite(temperature)
                or temperature < 0
                or not math.isfinite(timeout)
                or timeout <= 0
                or context_length <= 0
            ):
                raise ValueError("Invalid Ollama configuration.")
        except (ValueError, httpx.InvalidURL) as error:
            raise MissingProviderConfigurationError("Invalid Ollama configuration.") from error
        return cls(OllamaProviderConfig(model, base_url, temperature, timeout, context_length))

    def request_structured(self, request: StructuredRequest) -> StructuredResult:
        logger.info("Sending structured Ollama request with model=%s", self._config.model)
        options = {"temperature": self._config.temperature, "num_ctx": self._config.context_length}
        if request.stage in {"screenplay_review", "screenplay_generation"}:
            options["num_predict"] = SCREENPLAY_OUTPUT_TOKENS
        try:
            response = httpx.post(
                f"{self._config.base_url}/api/chat",
                json={
                    "model": self._config.model,
                    "messages": [
                        {"role": "system", "content": strict_json_instructions(request)},
                        {"role": "user", "content": request.input_text},
                    ],
                    "stream": False,
                    "format": request.response_model.model_json_schema(),
                    "options": options,
                },
                timeout=self._config.timeout_seconds,
                trust_env=False,
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("Ollama timed out.") from error
        except httpx.HTTPStatusError as error:
            logger.warning("Ollama request failed status=%s", error.response.status_code)
            if error.response.status_code == 404:
                raise MissingProviderConfigurationError(
                    "The configured Ollama model is not installed."
                ) from error
            raise ProviderRequestError("Ollama request failed.") from error
        except httpx.RequestError as error:
            logger.warning("Ollama request failed exception_class=%s", type(error).__name__)
            raise ProviderRequestError("Ollama could not be reached.") from error

        content = None
        try:
            payload = response.json()
            if (
                not isinstance(payload, dict)
                or payload.get("done") is not True
                or payload.get("error")
            ):
                raise ValueError("Ollama did not complete the response.")
            message = payload.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Ollama returned no text.")
            if payload.get("done_reason") == "length":
                raise ValueError("Ollama response was truncated.")
            output = request.response_model.model_validate_json(content)
        except ValueError as error:
            logger.warning("Ollama output validation failed model=%s", self._config.model)
            raise MalformedProviderResponseError(
                "Ollama returned an invalid structured response.",
                raw_output=content if isinstance(content, str) else None,
            ) from error
        actual_model = payload.get("model")
        return StructuredResult(
            output=output,
            model=actual_model
            if isinstance(actual_model, str) and actual_model
            else self._config.model,
            raw_output=content,
        )
