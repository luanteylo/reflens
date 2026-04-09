"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REFLENS_", env_file=".env")

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    ai_provider: str = Field(
        default="claude", description="claude, openai, or ollama"
    )
    ai_model: str = Field(
        default="claude-sonnet-4-6",
        description="Model for summarization and tagging",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="sentence-transformers model for embeddings",
    )

    # Database
    database_url: str = "sqlite:///reflens.db"

    # GROBID
    grobid_url: str = "http://localhost:8070"

    # Storage paths
    storage_path: Path = Path("./storage")
    chroma_path: Path = Path("./chroma_data")

    # Server
    host: str = "127.0.0.1"
    port: int = 8000


def get_settings() -> Settings:
    return Settings()
