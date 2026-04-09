"""Dependency injection for the FastAPI API layer."""

from fastapi import HTTPException, Request

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


def get_user_id(request: Request) -> str:
    """Return the current user ID.

    In local mode (auth_enabled=False): returns "local".
    In auth mode: decodes JWT from HttpOnly cookie.
    """
    from reflens.config import get_settings

    settings = get_settings()
    if not settings.auth_enabled:
        return "local"

    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from reflens.auth.security import decode_token

    try:
        payload = decode_token(token, settings)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
