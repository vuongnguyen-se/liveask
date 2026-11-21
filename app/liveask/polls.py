"""Polls: the host creates, opens and closes them; the audience votes (and may change its vote)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, StringConstraints

from liveask import events
from liveask.common import (
    AuthHeader,
    Pool,
    RequiredDevice,
    load_room,
    require_host_token,
)
from liveask.errors import ApiError

router = APIRouter(prefix="/api", tags=["polls"])

Option = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class PollIn(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    options: Annotated[list[Option], Field(min_length=2, max_length=6)]


class PollPatch(BaseModel):
    status: Literal["open", "closed"]


class VoteIn(BaseModel):
    option_index: Annotated[int, Field(ge=0, le=5)]


def poll_json(row: dict, counts: dict[int, int]) -> dict:
    n = len(row["options"])
    return {
        "id": row["id"],
        "question": row["question"],
        "options": row["options"],
        "status": row["status"],
        "counts": [counts.get(i, 0) for i in range(n)],
        "total": sum(counts.values()),
    }


async def _counts(conn: AsyncConnection, poll_ids: list[int]) -> dict[int, dict[int, int]]:
    result: dict[int, dict[int, int]] = {pid: {} for pid in poll_ids}
    if poll_ids:
        cur = await conn.execute(
            "SELECT poll_id, option_index, count(*) FROM poll_vote "
            "WHERE poll_id = ANY(%s) GROUP BY poll_id, option_index",
            (poll_ids,),
        )
        for poll_id, option, n in await cur.fetchall():
            result[poll_id][option] = n
    return result


async def poll_by_id(conn: AsyncConnection, poll_id: int) -> dict | None:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, question, options, status FROM poll WHERE id = %s", (poll_id,)
        )
        row = await cur.fetchone()
    if row is None:
        return None
    return poll_json(row, (await _counts(conn, [poll_id]))[poll_id])


async def list_polls(
    conn: AsyncConnection, room_id: int, device: uuid.UUID | None, include_draft: bool
) -> tuple[list[dict], dict[str, int]]:
    """The room's polls (drafts only for the host) and this device's votes {poll_id: option}."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT id, question, options, status FROM poll WHERE room_id = %s "
            "AND (%s OR status <> 'draft') ORDER BY id",
            (room_id, include_draft),
        )
        rows = await cur.fetchall()
    counts = await _counts(conn, [r["id"] for r in rows])
    mine: dict[str, int] = {}
    if device is not None and rows:
        cur2 = await conn.execute(
            "SELECT poll_id, option_index FROM poll_vote "
            "WHERE device_id = %s AND poll_id = ANY(%s)",
            (device, [r["id"] for r in rows]),
        )
        mine = {str(pid): opt for pid, opt in await cur2.fetchall()}
    return [poll_json(r, counts[r["id"]]) for r in rows], mine


async def _load_poll_for_update(conn: AsyncConnection, poll_id: int) -> dict:
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            "SELECT p.id, p.question, p.options, p.status, r.code AS room_code, "
            "r.host_token_hash, (r.closed_at IS NOT NULL) AS room_closed "
            "FROM poll p JOIN room r ON r.id = p.room_id "
            "WHERE p.id = %s AND r.expires_at > now() FOR UPDATE OF p",
            (poll_id,),
        )
        row = await cur.fetchone()
    if row is None:
        raise ApiError(404, "poll_not_found", "poll not found")
    return row


@router.post("/rooms/{code}/polls", status_code=201)
async def create_poll(
    code: str, body: PollIn, pool: Pool, authorization: AuthHeader = None
) -> dict:
    room = await load_room(pool, code)
    require_host_token(room, authorization)
    if room["closed_at"] is not None:
        raise ApiError(409, "room_closed", "this room is closed")
    async with pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO poll (room_id, question, options) VALUES (%s, %s, %s) RETURNING id",
            (room["id"], body.question, Jsonb(body.options)),
        )
        poll_id = (await cur.fetchone())[0]
        # No notify: a draft is private to the host. poll.created is sent when it is opened.
        return await poll_by_id(conn, poll_id)


@router.patch("/polls/{poll_id}")
async def set_poll_status(
    poll_id: int, body: PollPatch, pool: Pool, authorization: AuthHeader = None
) -> dict:
    async with pool.connection() as conn:
        p = await _load_poll_for_update(conn, poll_id)
        require_host_token({"host_token_hash": p["host_token_hash"]}, authorization)
        if p["room_closed"]:
            raise ApiError(409, "room_closed", "this room is closed")
        if body.status != p["status"]:
            allowed = {("draft", "open"), ("open", "closed")}
            if (p["status"], body.status) not in allowed:
                msg = f"cannot change a {p['status']} poll to {body.status}"
                raise ApiError(409, "invalid_transition", msg)
            await conn.execute("UPDATE poll SET status = %s WHERE id = %s", (body.status, poll_id))
            first_open = p["status"] == "draft"
            await events.notify(
                conn, p["room_code"], "poll.created" if first_open else "poll.updated", poll_id
            )
        return await poll_by_id(conn, poll_id)


@router.post("/polls/{poll_id}/vote")
async def vote(poll_id: int, body: VoteIn, device: RequiredDevice, pool: Pool) -> dict:
    async with pool.connection() as conn:
        p = await _load_poll_for_update(conn, poll_id)
        if p["status"] == "draft":
            raise ApiError(404, "poll_not_found", "poll not found")
        if p["room_closed"]:
            raise ApiError(409, "room_closed", "this room is closed")
        if p["status"] != "open":
            raise ApiError(409, "poll_closed", "this poll is not open")
        if body.option_index >= len(p["options"]):
            raise ApiError(422, "validation_error", "option_index out of range")
        # One row per (poll, device): voting again just changes the chosen option.
        await conn.execute(
            "INSERT INTO poll_vote (poll_id, device_id, option_index) VALUES (%s, %s, %s) "
            "ON CONFLICT (poll_id, device_id) DO UPDATE SET option_index = EXCLUDED.option_index",
            (poll_id, device, body.option_index),
        )
        await events.notify(conn, p["room_code"], "poll.updated", poll_id)
        return await poll_by_id(conn, poll_id)
