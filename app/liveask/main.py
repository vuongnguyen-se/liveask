"""FastAPI app: probes now; rooms, questions, polls and WebSockets arrive in later tasks."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from liveask import db, errors, rooms
from liveask.config import get_settings

log = logging.getLogger("liveask")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    app.state.pool = await db.open_pool(settings.database_url) if settings.database_url else None
    yield
    if app.state.pool is not None:
        await app.state.pool.close()


app = FastAPI(title="LiveAsk", version=get_settings().app_version, lifespan=lifespan)
errors.install(app)
app.include_router(rooms.router)


@app.get("/healthz")
async def healthz() -> dict:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict:
    """Readiness: the database is reachable. (The LISTEN connection joins this check in D1-05.)"""
    pool = app.state.pool
    if pool is None:
        raise HTTPException(status_code=503, detail="database not configured")
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
