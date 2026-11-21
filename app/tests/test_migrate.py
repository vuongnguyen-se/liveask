import asyncio

import psycopg

from liveask import migrate

TABLES = {"room", "question", "question_vote", "poll", "poll_vote"}


async def test_migrate_twice_is_safe(db_url):
    await migrate.run(db_url)
    await migrate.run(db_url)  # idempotent: the second run must not fail
    async with await psycopg.AsyncConnection.connect(db_url) as conn:
        cur = await conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
        assert TABLES <= {row[0] for row in await cur.fetchall()}


async def test_three_migrations_at_once_do_not_race(db_url):
    await asyncio.gather(migrate.run(db_url), migrate.run(db_url), migrate.run(db_url))
