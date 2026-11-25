"""FastAPI application factory: REST API + the built React frontend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__, config
from .api import router
from .db import Database

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}')

SECURITY_HEADERS = {
    # R8: no inline scripts, no third-party content.
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                               "img-src 'self' data:; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def create_app(db: Database | None = None, fetcher=None) -> FastAPI:
    database = db or Database(config.DB_PATH)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        database.fail_interrupted()  # NFR-15
        yield

    app = FastAPI(title="Automated Quality Gatekeeper", version=__version__, lifespan=lifespan)
    app.state.db = database
    app.state.fetcher = fetcher

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    app.include_router(router)
    _mount_frontend(app)
    return app


def _mount_frontend(app: FastAPI) -> None:
    """Serve the built React app from the same origin (one container in v0.1)."""
    index = config.STATIC_DIR / "index.html"
    if not index.exists():
        return
    app.mount("/assets", StaticFiles(directory=config.STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        return FileResponse(index)


app = create_app()
