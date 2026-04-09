"""Factory for creating AI provider instances based on config."""

from reflens.ai.provider import AIProvider
from reflens.config import Settings


def create_ai_provider(settings: Settings) -> AIProvider:
    """Create an AI provider based on the current configuration."""
    if settings.ai_provider == "claude":
        if not settings.anthropic_api_key:
            raise ValueError(
                "REFLENS_ANTHROPIC_API_KEY is required when ai_provider=claude"
            )
        from reflens.ai.claude import ClaudeProvider

        return ClaudeProvider(
            api_key=settings.anthropic_api_key,
            model=settings.ai_model,
        )
    elif settings.ai_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "REFLENS_OPENAI_API_KEY is required when ai_provider=openai"
            )
        from reflens.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.ai_model,
            base_url=settings.openai_base_url or None,
        )
    elif settings.ai_provider == "ollama":
        from reflens.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key="ollama",
            model=settings.ai_model or "llama3.1",
            base_url=settings.openai_base_url or "http://localhost:11434/v1",
        )
    else:
        raise ValueError(f"Unknown AI provider: {settings.ai_provider}")
