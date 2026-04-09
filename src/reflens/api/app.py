"""FastAPI application factory."""

import socket

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from reflens import __version__
from reflens.api.routes import auth, authors, collections, papers, search, searches, tags, tasks
from reflens.api.schemas import HealthResponse


def _cors_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    hostname = socket.gethostname()
    if hostname != "localhost":
        origins.append(f"http://{hostname}:3000")
    # Allow access from any IP on the local network
    try:
        ip = socket.gethostbyname(hostname)
        if ip != "127.0.0.1":
            origins.append(f"http://{ip}:3000")
    except socket.gaierror:
        pass
    return origins


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
