"""Factory for creating AI provider instances based on config."""

from reflens.ai.provider import AIProvider, ProviderProfile
from reflens.config import Settings

# Profile for local models (Ollama, etc.)
LOCAL_PROFILE = ProviderProfile(
    max_context_chars=3000,
    max_output_tokens=500,
    use_compact_prompts=True,
    abstract_only_relevance=True,
)


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Parse 'provider/model' into (provider, model). Default provider is ollama."""
    if "/" in spec:
        provider, model = spec.split("/", 1)
        return provider.strip(), model.strip()
    return "ollama", spec.strip()


def list_available_models(settings: Settings) -> list[dict]:
    """List all configured models with their provider info."""
    models = []

    if settings.ai_models:
        for spec in settings.ai_models.split(","):
            spec = spec.strip()
            if not spec:
                continue
            provider, model = parse_model_spec(spec)
            models.append({
                "id": spec,
                "provider": provider,
                "model": model,
                "local": provider == "ollama",
            })
    else:
        # Fallback: just the default model
        models.append({
            "id": f"{settings.ai_provider}/{settings.ai_model}",
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "local": settings.ai_provider == "ollama",
        })

    return models


def create_ai_provider(settings: Settings, model_id: str | None = None) -> AIProvider:
    """Create an AI provider. If model_id is given (e.g. 'ollama/mistral'), use that."""
    if model_id:
        provider, model = parse_model_spec(model_id)
    else:
        provider = settings.ai_provider
        model = settings.ai_model

    if provider == "claude":
        if not settings.anthropic_api_key:
            raise ValueError(
                "REFLENS_ANTHROPIC_API_KEY is required when using claude models"
            )
        from reflens.ai.claude import ClaudeProvider

        return ClaudeProvider(
            api_key=settings.anthropic_api_key,
            model=model,
        )
    elif provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "REFLENS_OPENAI_API_KEY is required when using openai models"
            )
        from reflens.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=model,
            base_url=settings.openai_base_url or None,
        )
    elif provider == "ollama":
        from reflens.ai.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key="ollama",
            model=model,
            base_url=settings.openai_base_url or "http://localhost:11434/v1",
            profile=LOCAL_PROFILE,
        )
    else:
        raise ValueError(f"Unknown AI provider: {provider}")
