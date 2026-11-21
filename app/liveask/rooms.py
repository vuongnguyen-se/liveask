"""Rooms: create, read, close. Questions and polls are added to the snapshot in later tasks."""

from __future__ import annotations

import re
from typing import Annotated

import psycopg.errors
from fastapi import APIRouter, Depends, Header, Request, Response
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import BaseModel, StringConstraints

from liveask import security
from liveask.errors import ApiError

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

CODE_RE = re.compile(r"^[A-Z0-9]{6}$")


class RoomIn(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


def get_pool(request: Request) -> AsyncConnectionPool:
    pool = request.app.state.pool
    if pool is None:
        raise ApiError(503, "unavailable", "database not configured")
    return pool


Pool = Annotated[AsyncConnectionPool, Depends(get_pool)]


async def load_room(pool: AsyncConnectionPool, code: str) -> dict:
    """Return the room row, or raise 404. Expired rooms count as gone."""
    code = code.upper()
    if not CODE_RE.match(code):
        raise ApiError(404, "room_not_found", "room not found")
    async with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        await cur.execute("SELECT * FROM room WHERE code = %s AND expires_at > now()", (code,))
        room = await cur.fetchone()
    if room is None:
        raise ApiError(404, "room_not_found", "room not found")
    return room


def bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return None


def require_host_token(room: dict, authorization: str | None) -> None:
    """401 if no token was sent, 403 if it is wrong."""
    token = bearer_token(authorization)
    if token is None:
        raise ApiError(401, "host_token_required", "host token required")
    if not security.token_matches(token, room["host_token_hash"]):
        raise ApiError(403, "forbidden", "wrong host token")


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
async def get_room(code: str, pool: Pool) -> dict:
    room = await load_room(pool, code)
    return {
        "code": room["code"],
        "title": room["title"],
        "closed": room["closed_at"] is not None,
        "questions": [],  # D1-03
        "polls": [],  # D1-04
        "my_votes": {"questions": [], "polls": {}},
    }


@router.post("/{code}/close", status_code=204)
async def close_room(
    code: str, pool: Pool, authorization: Annotated[str | None, Header()] = None
) -> Response:
    room = await load_room(pool, code)
    require_host_token(room, authorization)
    async with pool.connection() as conn:
        await conn.execute(
            "UPDATE room SET closed_at = COALESCE(closed_at, now()) WHERE id = %s", (room["id"],)
        )
    # D1-05: pg_notify('liveask_events', room.closed) goes in this same transaction.
    return Response(status_code=204)
