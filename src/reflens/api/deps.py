"""Dependency injection for the FastAPI API layer."""

from reflens.config import Settings
from reflens.core.engine import RefLensEngine

_engine: RefLensEngine | None = None


def get_engine() -> RefLensEngine:
    """Return the singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = RefLensEngine(Settings())
    return _engine


def set_engine(engine: RefLensEngine) -> None:
    """Override the engine instance (used in tests)."""
    global _engine
    _engine = engine


def get_user_id() -> str:
    """Return the current user ID. Hardcoded for local mode."""
    return "local"
