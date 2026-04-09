"""FastAPI application factory."""

import socket

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from reflens import __version__
from reflens.api.routes import auth, authors, collections, papers, search, searches, tags, tasks
from reflens.api.schemas import HealthResponse


def _cors_origins() -> list[str]:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    hostname = socket.gethostname()
    if hostname != "localhost":
        origins.append(f"http://{hostname}:3000")
    # Add all network IPs
    try:
        import subprocess
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=2
        )
        for ip in result.stdout.strip().split():
            origins.append(f"http://{ip}:3000")
    except Exception:
        pass
    return list(set(origins))


def create_app() -> FastAPI:
    app = FastAPI(
        title="RefLens API",
        version=__version__,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(auth.router)
    v1.include_router(papers.router)
    v1.include_router(search.router)
    v1.include_router(tags.router)
    v1.include_router(authors.router)
    v1.include_router(tasks.router)
    v1.include_router(collections.router)
    v1.include_router(searches.router)

    @v1.get("/health", response_model=HealthResponse, tags=["system"])
    def health():
        return HealthResponse(status="ok", version=__version__)

    @v1.get("/health/ai", tags=["system"])
    def ai_info():
        from reflens.ai.factory import list_available_models
        from reflens.config import get_settings
        settings = get_settings()
        return {
            "provider": settings.ai_provider,
            "model": settings.ai_model,
            "default": f"{settings.ai_provider}/{settings.ai_model}",
            "models": list_available_models(settings),
        }

    @v1.get("/preferences", tags=["system"])
    def get_preferences(request: Request):
        from reflens.api.deps import get_user_id
        from reflens.db.session import get_session
        from sqlalchemy import select
        from reflens.db.models import UserPreferences

        user_id = get_user_id(request)
        session = get_session()
        try:
            prefs = session.execute(
                select(UserPreferences).where(UserPreferences.user_id == user_id)
            ).scalar_one_or_none()
            if prefs:
                return {
                    "default_model": prefs.default_model,
                    "search_limit": prefs.search_limit,
                    "explain_by_default": prefs.explain_by_default,
                    "context_length": prefs.context_length,
                }
            return {
                "default_model": None,
                "search_limit": 10,
                "explain_by_default": True,
                "context_length": 6000,
            }
        finally:
            session.close()

    @v1.put("/preferences", tags=["system"])
    def update_preferences(request: Request, body: dict):
        from reflens.api.deps import get_user_id
        from reflens.db.session import get_session
        from sqlalchemy import select
        from reflens.db.models import UserPreferences

        user_id = get_user_id(request)
        session = get_session()
        try:
            prefs = session.execute(
                select(UserPreferences).where(UserPreferences.user_id == user_id)
            ).scalar_one_or_none()
            if prefs is None:
                prefs = UserPreferences(user_id=user_id)
                session.add(prefs)
            if "default_model" in body:
                prefs.default_model = body["default_model"]
            if "search_limit" in body:
                prefs.search_limit = max(1, min(50, body["search_limit"]))
            if "explain_by_default" in body:
                prefs.explain_by_default = bool(body["explain_by_default"])
            if "context_length" in body:
                prefs.context_length = max(1000, min(100000, body["context_length"]))
            session.commit()
            return {
                "default_model": prefs.default_model,
                "search_limit": prefs.search_limit,
                "explain_by_default": prefs.explain_by_default,
                "context_length": prefs.context_length,
            }
        finally:
            session.close()

    @v1.get("/health/usage", tags=["system"])
    def usage_stats(request: Request):
        from reflens.api.deps import get_user_id
        from reflens.db.session import get_session
        from sqlalchemy import func, select
        from reflens.db.models import UsageLog

        user_id = get_user_id(request)
        session = get_session()
        try:
            # Total usage
            totals = session.execute(
                select(
                    func.sum(UsageLog.prompt_tokens),
                    func.sum(UsageLog.completion_tokens),
                    func.sum(UsageLog.total_tokens),
                    func.sum(UsageLog.cost_usd),
                    func.count(UsageLog.id),
                ).where(UsageLog.user_id == user_id)
            ).one()

            # Per-model breakdown
            by_model = session.execute(
                select(
                    UsageLog.provider,
                    UsageLog.model,
                    func.sum(UsageLog.prompt_tokens),
                    func.sum(UsageLog.completion_tokens),
                    func.sum(UsageLog.cost_usd),
                    func.count(UsageLog.id),
                )
                .where(UsageLog.user_id == user_id)
                .group_by(UsageLog.provider, UsageLog.model)
            ).all()

            return {
                "total_prompt_tokens": totals[0] or 0,
                "total_completion_tokens": totals[1] or 0,
                "total_tokens": totals[2] or 0,
                "total_cost_usd": round(totals[3] or 0, 4),
                "total_requests": totals[4] or 0,
                "by_model": [
                    {
                        "provider": r[0],
                        "model": r[1],
                        "prompt_tokens": r[2] or 0,
                        "completion_tokens": r[3] or 0,
                        "cost_usd": round(r[4] or 0, 4),
                        "requests": r[5] or 0,
                    }
                    for r in by_model
                ],
            }
        finally:
            session.close()

    @v1.get("/health/stats", tags=["system"])
    def stats(request: Request):
        from reflens.api.deps import get_engine, get_user_id
        engine = get_engine()
        user_id = get_user_id(request)
        total_papers = engine.count_papers(user_id)
        collections = engine.list_collections(user_id)

        # Count storage size
        import os
        storage_bytes = 0
        storage_path = engine.settings.storage_path / user_id
        if storage_path.exists():
            for f in storage_path.rglob("*"):
                if f.is_file():
                    storage_bytes += f.stat().st_size

        def _count_collections(cols: list) -> int:
            count = len(cols)
            for c in cols:
                count += _count_collections(c.get("children", []))
            return count

        return {
            "papers": total_papers,
            "collections": _count_collections(collections),
            "storage_bytes": storage_bytes,
            "storage_mb": round(storage_bytes / (1024 * 1024), 1),
        }

    @v1.get("/health/grobid", tags=["system"])
    def grobid_health():
        import httpx
        from reflens.config import get_settings
        settings = get_settings()
        try:
            resp = httpx.get(f"{settings.grobid_url}/api/isalive", timeout=3)
            return {"status": "ok" if resp.status_code == 200 else "down"}
        except Exception:
            return {"status": "down"}

    app.include_router(v1)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/api/v1/docs")

    return app
