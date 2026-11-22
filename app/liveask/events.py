"""Cross-pod events. Every write that clients must see calls notify() in its own transaction.

Postgres delivers a NOTIFY only when the transaction commits, so clients never hear about
data that was rolled back. The payload carries only the type and ids (the limit is 8000
bytes); the pods read the object from the database (see hub.py, task D1-05).
"""

from __future__ import annotations

import json

from psycopg import AsyncConnection

CHANNEL = "liveask_events"


async def notify(conn: AsyncConnection, room: str, type_: str, id_: int | None = None) -> None:
    payload = {"room": room, "type": type_}
    if id_ is not None:
        payload["id"] = id_
    await conn.execute("SELECT pg_notify(%s, %s)", (CHANNEL, json.dumps(payload)))
