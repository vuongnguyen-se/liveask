"""FastAPI app: probes now; rooms, questions, polls and WebSockets arrive in later tasks."""

from __future__ import annotations

import logging
import mimetypes
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from liveask import db, errors, hub, landing, polls, questions, rooms
from liveask.config import get_settings

log = logging.getLogger("liveask")
STATIC_DIR = Path(__file__).parent / "static"

# The slim Python image has no mime entry for woff2 and would send application/octet-stream.
mimetypes.add_type("font/woff2", ".woff2")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app.state.pool = None
    app.state.hub = None
    if settings.database_url:
        app.state.pool = await db.open_pool(settings.database_url)
        app.state.hub = hub.Hub(
            settings.database_url,
            app.state.pool,
            settings.pod_name,
            settings.max_connections_per_room,
        )
        await app.state.hub.start()
    yield
    if app.state.hub is not None:
        await app.state.hub.stop()  # closes sockets with 1012 so clients reconnect elsewhere
    if app.state.pool is not None:
        await app.state.pool.close()


app = FastAPI(title="LiveAsk", version=get_settings().app_version, lifespan=lifespan)
errors.install(app)
app.include_router(rooms.router)
app.include_router(questions.router)
app.include_router(polls.router)
app.include_router(hub.router)
app.include_router(landing.router)


@app.get("/healthz")
async def healthz() -> dict:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict:
    """Readiness: database reachable AND the LISTEN connection alive; 503 while shutting down."""
    pool, live = app.state.pool, app.state.hub
    if pool is None or live is None:
        raise HTTPException(status_code=503, detail="database not configured")
    if live.shutting_down:
        raise HTTPException(status_code=503, detail="shutting down")
    if not live.listening:
        raise HTTPException(status_code=503, detail="event listener not connected")
    try:
        await db.ping(pool)
    except Exception as exc:  # noqa: BLE001 - any backend failure means "not ready"
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}


@app.get("/burn")
def burn(ms: int = 200) -> dict:
    """Spends CPU for a bounded time so the HPA can be load-tested."""
    ms = max(1, min(ms, 2000))
    end = time.monotonic() + ms / 1000
    n = 0
    while time.monotonic() < end:
        n += 1
    return {"iterations": n}


# --- pages (plain HTML; the JS in /static/app.js does the rest) ---------------------------


def _page(name: str) -> FileResponse:
    # no-cache: a new deploy must not leave browsers on an old page
    return FileResponse(STATIC_DIR / name, headers={"Cache-Control": "no-cache"})


@app.get("/", include_in_schema=False)
async def page_index() -> FileResponse:
    return _page("index.html")


@app.get("/r/{code}", include_in_schema=False)
async def page_audience(code: str) -> FileResponse:
    return _page("audience.html")


@app.get("/host/{code}", include_in_schema=False)
async def page_host(code: str) -> FileResponse:
    return _page("host.html")  # the host token is in the #fragment, which never reaches us


@app.get("/screen/{code}", include_in_schema=False)
async def page_screen(code: str) -> FileResponse:
    return _page("screen.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
