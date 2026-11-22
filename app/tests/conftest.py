"""Database tests need a real PostgreSQL. Set TEST_DATABASE_URL, e.g.

    postgresql://liveask:liveask-local-only@127.0.0.1:5432/liveask

Without it those tests are skipped. Each test gets its own schema, so tests never
see each other's data.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from urllib.parse import quote

import psycopg
import pytest
from fastapi.testclient import TestClient

from liveask import migrate, ratelimit
from liveask.main import app

if sys.platform == "win32":  # psycopg async cannot use Windows' default ProactorEventLoop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
async def db_url():
    """A database URL whose search_path points at a fresh, empty schema."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    schema = f"t_{uuid.uuid4().hex[:12]}"
    async with await psycopg.AsyncConnection.connect(TEST_DATABASE_URL, autocommit=True) as c:
        await c.execute(f"CREATE SCHEMA {schema}")
    sep = "&" if "?" in TEST_DATABASE_URL else "?"
    options = quote(f"-c search_path={schema}")
    yield f"{TEST_DATABASE_URL}{sep}options={options}"
    async with await psycopg.AsyncConnection.connect(TEST_DATABASE_URL, autocommit=True) as c:
        await c.execute(f"DROP SCHEMA {schema} CASCADE")


@pytest.fixture(autouse=True)
def fresh_room_limit():
    """The room-creation count lives in memory: start every test with an empty one."""
    ratelimit.room_creations.clear()


@pytest.fixture
def client(monkeypatch, db_url):
    """A test client on a freshly migrated, empty schema."""
    asyncio.run(migrate.run(db_url))
    monkeypatch.setenv("DATABASE_URL", db_url)
    with TestClient(app) as c:
        yield c
