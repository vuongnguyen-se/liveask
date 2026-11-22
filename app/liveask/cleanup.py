"""Delete expired rooms. Run nightly as the Kubernetes CronJob: ``python -m liveask.cleanup``.

Rooms expire 24 hours after creation (the API already treats them as gone). This removes
their rows, and the questions, votes and polls under them (ON DELETE CASCADE). It is safe to
run any time and any number of times: it only touches rooms whose ``expires_at`` has passed.
"""

from __future__ import annotations

import asyncio
import logging
import sys

import psycopg

from liveask.config import get_settings

log = logging.getLogger("liveask.cleanup")


async def run(url: str) -> int:
    """Delete the expired rooms and return how many there were."""
    async with await psycopg.AsyncConnection.connect(url, autocommit=True) as conn:
        cur = await conn.execute("DELETE FROM room WHERE expires_at < now()")
        return cur.rowcount


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    url = get_settings().database_url
    if not url:
        log.error("DATABASE_URL is not set")
        return 1
    if sys.platform == "win32":  # psycopg async cannot use Windows' default ProactorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    removed = asyncio.run(run(url))
    log.info("removed %d expired room%s", removed, "" if removed == 1 else "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
