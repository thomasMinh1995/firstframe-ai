import logging
import os

from dotenv import load_dotenv

from app.application.ai_provider import MissingProviderConfigurationError, StructuredProvider
from app.infrastructure.ollama_provider import OllamaProvider
from app.infrastructure.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


def create_provider() -> StructuredProvider:
    load_dotenv()
    provider = os.getenv("AI_PROVIDER", "auto").strip().lower() or "auto"
    if provider == "auto":
        provider = "openai" if os.getenv("OPENAI_API_KEY", "").strip() else "ollama"
    logger.info("Selected AI provider=%s", provider)
    if provider == "openai":
        return OpenAIProvider.from_env()
    if provider == "ollama":
        return OllamaProvider.from_env()
    raise MissingProviderConfigurationError("AI_PROVIDER must be auto, openai, or ollama.")
