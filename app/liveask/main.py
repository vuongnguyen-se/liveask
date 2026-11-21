"""FastAPI app: probes now; rooms, questions, polls and WebSockets arrive in later tasks."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from liveask import db, errors, hub, polls, questions, rooms
from liveask.config import get_settings

log = logging.getLogger("liveask")


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
