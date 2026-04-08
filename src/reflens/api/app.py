"""FastAPI application factory."""

import socket

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from reflens import __version__
from reflens.api.routes import authors, collections, papers, search, searches, tags, tasks
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
