"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REFLENS_", env_file=".env", extra="ignore"
    )

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    ai_provider: str = Field(
        default="claude", description="Default provider: claude, openai, or ollama"
    )
    ai_model: str = Field(
        default="claude-sonnet-4-6",
        description="Default model for summarization and tagging",
    )
    ai_models: str = Field(
        default="",
        description="Comma-separated list of available models, e.g. ollama/mistral,ollama/llama3.1,claude/claude-sonnet-4-6",
    )
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
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

    # Auth
    auth_enabled: bool = False
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = ""
    mail_server: str = ""
    mail_port: int = 587
    mail_starttls: bool = True
    mail_ssl_tls: bool = False

    # Frontend
    frontend_url: str = "http://localhost:3000"


def get_settings() -> Settings:
    return Settings()
