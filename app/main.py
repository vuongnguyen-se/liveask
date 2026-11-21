"""Notes API: a small FastAPI service used to exercise the EKS platform.

Storage is PostgreSQL (Amazon RDS) when DATABASE_URL is set, otherwise an
in-memory store so the app runs anywhere (tests, kind, docker run).
"""

from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Protocol

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_VERSION = os.getenv("APP_VERSION", "dev")


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class Note(BaseModel):
    id: int
    text: str
    created_at: datetime


class Store(Protocol):
    def list(self) -> list[Note]: ...
    def add(self, text: str) -> Note: ...
    def ping(self) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._notes: list[Note] = []

    def list(self) -> list[Note]:
        return list(reversed(self._notes))

    def add(self, text: str) -> Note:
        note = Note(id=len(self._notes) + 1, text=text, created_at=datetime.now(timezone.utc))
        self._notes.append(note)
        return note

    def ping(self) -> None:
        return None


class PostgresStore:
    def __init__(self, url: str) -> None:
        from psycopg_pool import ConnectionPool

        self._pool = ConnectionPool(url, min_size=1, max_size=5, open=True)
        with self._pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id SERIAL PRIMARY KEY,
                    text VARCHAR(500) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )

    def list(self) -> list[Note]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT id, text, created_at FROM notes ORDER BY id DESC LIMIT 100"
            ).fetchall()
        return [Note(id=r[0], text=r[1], created_at=r[2]) for r in rows]

    def add(self, text: str) -> Note:
        with self._pool.connection() as conn:
            r = conn.execute(
                "INSERT INTO notes (text) VALUES (%s) RETURNING id, text, created_at", (text,)
            ).fetchone()
        return Note(id=r[0], text=r[1], created_at=r[2])

    def ping(self) -> None:
        with self._pool.connection() as conn:
            conn.execute("SELECT 1")

    def close(self) -> None:
        self._pool.close()


def build_store() -> Store:
    url = os.getenv("DATABASE_URL")
    return PostgresStore(url) if url else MemoryStore()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.store = build_store()
    yield
    close = getattr(app.state.store, "close", None)
    if close:
        close()


app = FastAPI(title="Notes API", version=APP_VERSION, lifespan=lifespan)


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up. Never touches the database."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    """Readiness: the pod can serve traffic (database reachable)."""
    try:
        app.state.store.ping()
    except Exception as exc:  # noqa: BLE001 - report any backend failure as not ready
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    return {"status": "ready"}


@app.get("/")
def info() -> dict:
    """Shows which pod answered: useful to watch the load balancer and HPA at work."""
    return {
        "service": "notes-api",
        "version": APP_VERSION,
        "pod": socket.gethostname(),
        "storage": type(app.state.store).__name__,
    }


@app.get("/notes", response_model=list[Note])
def list_notes() -> list[Note]:
    return app.state.store.list()


@app.post("/notes", response_model=Note, status_code=201)
def create_note(body: NoteIn) -> Note:
    return app.state.store.add(body.text.strip())


@app.get("/burn")
def burn(ms: int = 200) -> dict:
    """Spends CPU for a bounded time so you can load-test the HPA."""
    ms = max(1, min(ms, 2000))
    end = datetime.now(timezone.utc).timestamp() + ms / 1000
    n = 0
    while datetime.now(timezone.utc).timestamp() < end:
        n += 1
    return {"iterations": n}
