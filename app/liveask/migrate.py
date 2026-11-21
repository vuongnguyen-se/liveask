"""Apply schema.sql. Run as the Kubernetes initContainer: ``python -m liveask.migrate``.

A Postgres advisory lock makes two pods that start at the same time take turns
instead of racing on CREATE TABLE.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import psycopg

from liveask.config import get_settings

LOCK_ID = 4242
SCHEMA_FILE = Path(__file__).with_name("schema.sql")
log = logging.getLogger("liveask.migrate")


async def run(url: str) -> None:
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as conn:
        await conn.execute("SELECT pg_advisory_lock(%s)", (LOCK_ID,))
        try:
            await conn.execute(sql)  # no parameters, so several statements are allowed
        finally:
            await conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))
    log.info("schema applied")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    url = get_settings().database_url
    if not url:
        log.error("DATABASE_URL is not set")
        return 1
    if sys.platform == "win32":  # psycopg async cannot use Windows' default ProactorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
