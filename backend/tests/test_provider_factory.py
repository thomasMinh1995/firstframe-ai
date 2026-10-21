import pytest

from app.application.ai_provider import MissingProviderConfigurationError
from app.infrastructure.ollama_provider import OllamaProvider
from app.infrastructure.openai_provider import OpenAIProvider
from app.infrastructure.provider_factory import create_provider


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch):
    monkeypatch.setattr("app.infrastructure.provider_factory.load_dotenv", lambda: None)
    monkeypatch.setattr("app.infrastructure.ollama_provider.load_dotenv", lambda: None)
    monkeypatch.setattr("app.infrastructure.openai_provider.load_dotenv", lambda: None)
    for key in (
        "AI_PROVIDER",
        "OPENAI_API_KEY",
        "MODEL",
        "TEMPERATURE",
        "OLLAMA_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_TIMEOUT_SECONDS",
        "OLLAMA_CONTEXT_LENGTH",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize("key", [None, "", "   "])
def test_auto_uses_local_model_without_openai_key(monkeypatch, key):
    if key is not None:
        monkeypatch.setenv("OPENAI_API_KEY", key)
    monkeypatch.setenv("MODEL", "gpt-cloud-model")
    monkeypatch.setattr(
        OpenAIProvider,
        "from_env",
        classmethod(lambda cls: pytest.fail("OpenAI must not be initialized without a key")),
    )
    provider = create_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider._config.model == "qwen2.5:3b"


def test_auto_prefers_openai_when_key_exists(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = object()
    monkeypatch.setattr(OpenAIProvider, "from_env", classmethod(lambda cls: provider))
    assert create_provider() is provider


def test_explicit_ollama_ignores_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "another-local-model")
    assert create_provider()._config.model == "another-local-model"


def test_explicit_openai_still_requires_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    with pytest.raises(MissingProviderConfigurationError):
        create_provider()


def test_unknown_provider_is_configuration_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "typo")
    with pytest.raises(MissingProviderConfigurationError):
        create_provider()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("OLLAMA_BASE_URL", "not-a-url"),
        ("OLLAMA_BASE_URL", ""),
        ("OLLAMA_TIMEOUT_SECONDS", "0"),
        ("OLLAMA_TIMEOUT_SECONDS", "nan"),
        ("OLLAMA_CONTEXT_LENGTH", "-1"),
        ("OLLAMA_CONTEXT_LENGTH", "invalid"),
        ("TEMPERATURE", "invalid"),
        ("TEMPERATURE", "inf"),
    ],
)
def test_invalid_ollama_configuration_is_rejected(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(MissingProviderConfigurationError):
        create_provider()
