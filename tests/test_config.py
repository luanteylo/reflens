"""Tests for configuration."""

from pathlib import Path

from reflens.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings()
        assert s.ai_provider == "claude"
        assert s.database_url == "sqlite:///reflens.db"
        assert s.port == 8000
        assert s.host == "127.0.0.1"

    def test_custom_values(self):
        s = Settings(
            anthropic_api_key="sk-test",
            ai_provider="openai",
            database_url="postgresql://localhost/reflens",
            port=9000,
        )
        assert s.anthropic_api_key == "sk-test"
        assert s.ai_provider == "openai"
        assert s.port == 9000

    def test_storage_path_is_path(self):
        s = Settings(storage_path=Path("/tmp/test"))
        assert isinstance(s.storage_path, Path)
