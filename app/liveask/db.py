"""Async PostgreSQL connection pool (psycopg 3)."""

from __future__ import annotations

from psycopg_pool import AsyncConnectionPool


async def open_pool(url: str, max_size: int = 10) -> AsyncConnectionPool:
    pool = AsyncConnectionPool(url, min_size=1, max_size=max_size, open=False)
    await pool.open(wait=True, timeout=15)
    return pool


async def ping(pool: AsyncConnectionPool) -> None:
    """Raises if the database cannot be reached."""
    async with pool.connection(timeout=2) as conn:
        await conn.execute("SELECT 1")
