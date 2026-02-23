"""Tests for AI provider factory."""

import pytest

from reflens.ai.factory import create_ai_provider
from reflens.ai.claude import ClaudeProvider
from reflens.ai.openai_provider import OpenAIProvider
from reflens.config import Settings


class TestAIFactory:
    def test_create_claude_provider(self):
        settings = Settings(
            ai_provider="claude",
            anthropic_api_key="test-key",
            ai_model="claude-sonnet-4-6",
        )
        provider = create_ai_provider(settings)
        assert isinstance(provider, ClaudeProvider)

    def test_create_openai_provider(self):
        settings = Settings(
            ai_provider="openai",
            openai_api_key="test-key",
            ai_model="gpt-4o",
        )
        provider = create_ai_provider(settings)
        assert isinstance(provider, OpenAIProvider)

    def test_raises_on_missing_claude_key(self):
        settings = Settings(ai_provider="claude", anthropic_api_key="")
        with pytest.raises(ValueError, match="REFLENS_ANTHROPIC_API_KEY"):
            create_ai_provider(settings)

    def test_raises_on_missing_openai_key(self):
        settings = Settings(ai_provider="openai", openai_api_key="")
        with pytest.raises(ValueError, match="REFLENS_OPENAI_API_KEY"):
            create_ai_provider(settings)

    def test_raises_on_unknown_provider(self):
        settings = Settings(ai_provider="unknown", anthropic_api_key="x")
        with pytest.raises(ValueError, match="Unknown AI provider"):
            create_ai_provider(settings)
