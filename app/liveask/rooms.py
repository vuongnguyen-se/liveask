"""Rooms: create, read, close, and the snapshot clients load on connect and reconnect."""

from __future__ import annotations

from typing import Annotated

import psycopg.errors
from fastapi import APIRouter, Response
from pydantic import BaseModel, StringConstraints

from liveask import events, polls, questions, security
from liveask.common import (
    AuthHeader,
    OptionalDevice,
    Pool,
    is_host,
    load_room,
    require_host_token,
)
from liveask.errors import ApiError

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


class RoomIn(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


@router.post("", status_code=201)
async def create_room(body: RoomIn, pool: Pool) -> dict:
    token = security.generate_host_token()
    token_hash = security.hash_token(token)
    for _ in range(10):  # a code clash is very unlikely, but the UNIQUE constraint decides
        code = security.generate_code()
        try:
            async with pool.connection() as conn:
                cur = await conn.execute(
                    "INSERT INTO room (code, title, host_token_hash) VALUES (%s, %s, %s) "
                    "RETURNING expires_at",
                    (code, body.title, token_hash),
                )
                row = await cur.fetchone()
        except psycopg.errors.UniqueViolation:
            continue
        return {
            "code": code,
            "title": body.title,
            "host_token": token,  # returned only now; only its hash is stored
            "audience_url": f"/r/{code}",
            "screen_url": f"/screen/{code}",
            "host_url": f"/host/{code}#t={token}",
            "expires_at": row[0].isoformat(),
        }
    raise ApiError(503, "unavailable", "could not allocate a room code")


@router.get("/{code}")
async def get_room(
    code: str, pool: Pool, device: OptionalDevice, authorization: AuthHeader = None
) -> dict:
    room = await load_room(pool, code)
    host = is_host(room, authorization)  # the host also sees hidden questions and draft polls
    async with pool.connection() as conn:
        qs, voted = await questions.list_questions(conn, room["id"], device, include_hidden=host)
        pl, my_poll_votes = await polls.list_polls(conn, room["id"], device, include_draft=host)
    return {
        "code": room["code"],
        "title": room["title"],
        "closed": room["closed_at"] is not None,
        "questions": qs,
        "polls": pl,
        "my_votes": {"questions": voted, "polls": my_poll_votes},
    }


@router.post("/{code}/close", status_code=204)
async def close_room(code: str, pool: Pool, authorization: AuthHeader = None) -> Response:
    room = await load_room(pool, code)
    require_host_token(room, authorization)
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE room SET closed_at = COALESCE(closed_at, now()) WHERE id = %s", (room["id"],)
        )
        await events.notify(conn, room["code"], "room.closed")
    return Response(status_code=204)
