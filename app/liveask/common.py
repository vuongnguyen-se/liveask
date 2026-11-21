"""Helpers shared by the room, question and poll routers."""

from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import Depends, Header, Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from liveask import security
from liveask.errors import ApiError

CODE_RE = re.compile(r"^[A-Z0-9]{6}$")


def get_pool(request: Request) -> AsyncConnectionPool:
    pool = request.app.state.pool
    if pool is None:
        raise ApiError(503, "unavailable", "database not configured")
    return pool


Pool = Annotated[AsyncConnectionPool, Depends(get_pool)]


def parse_device_id(value: str | None) -> uuid.UUID | None:
    """None if the header is absent; 400 if it is present but not a UUID."""
    if value is None:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError(400, "invalid_device_id", "X-Device-Id must be a UUID") from None


def optional_device_id(x_device_id: Annotated[str | None, Header()] = None) -> uuid.UUID | None:
    return parse_device_id(x_device_id)


def required_device_id(x_device_id: Annotated[str | None, Header()] = None) -> uuid.UUID:
    device = parse_device_id(x_device_id)
    if device is None:
        raise ApiError(400, "device_id_required", "X-Device-Id header required")
    return device


OptionalDevice = Annotated[uuid.UUID | None, Depends(optional_device_id)]
RequiredDevice = Annotated[uuid.UUID, Depends(required_device_id)]
AuthHeader = Annotated[str | None, Header()]


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


def is_host(room: dict, authorization: str | None) -> bool:
    token = bearer_token(authorization)
    return token is not None and security.token_matches(token, room["host_token_hash"])


def require_host_token(room: dict, authorization: str | None) -> None:
    """401 if no token was sent, 403 if it is wrong."""
    token = bearer_token(authorization)
    if token is None:
        raise ApiError(401, "host_token_required", "host token required")
    if not security.token_matches(token, room["host_token_hash"]):
        raise ApiError(403, "forbidden", "wrong host token")
