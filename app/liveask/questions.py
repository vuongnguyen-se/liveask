"""Questions: post (rate limited), toggle upvote, host moderation."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pydantic import BaseModel, StringConstraints

from liveask import events
from liveask.common import (
    AuthHeader,
    Pool,
    RequiredDevice,
    load_room,
    require_host_token,
)
from liveask.config import get_settings
from liveask.errors import ApiError

router = APIRouter(prefix="/api", tags=["questions"])

COLUMNS = "q.id, q.text, q.author_name, q.votes, q.status, q.created_at"


class QuestionIn(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=280)]
    author_name: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = (
        None
    )


class QuestionPatch(BaseModel):
    status: Literal["open", "answered", "hidden"]


def question_json(row: dict) -> dict:
    return {
        "id": row["id"],
        "text": row["text"],
        "author_name": row["author_name"] or None,
        "votes": row["votes"],
        "status": row["status"],
        "created_at": row["created_at"].isoformat(),
    }


async def list_questions(
    conn: AsyncConnection, room_id: int, device: uuid.UUID | None, include_hidden: bool
) -> tuple[list[dict], list[int]]:
    """Questions sorted by votes then newest, and the ids this device has voted for."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            f"SELECT {COLUMNS} FROM question q WHERE q.room_id = %s "
            "AND (%s OR q.status <> 'hidden') ORDER BY q.votes DESC, q.created_at DESC, q.id DESC",
            (room_id, include_hidden),
        )
        rows = await cur.fetchall()
    voted: list[int] = []
    if device is not None:
        cur2 = await conn.execute(
            "SELECT v.question_id FROM question_vote v JOIN question q ON q.id = v.question_id "
            "WHERE q.room_id = %s AND v.device_id = %s",
            (room_id, device),
        )
        voted = [r[0] for r in await cur2.fetchall()]
    return [question_json(r) for r in rows], voted


async def _load_question_for_update(conn: AsyncConnection, question_id: int) -> dict:
    """Lock the question row and return it with its room's code, state and token hash."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(
            f"SELECT {COLUMNS}, r.code AS room_code, r.host_token_hash, "
            "(r.closed_at IS NOT NULL) AS room_closed "
            "FROM question q JOIN room r ON r.id = q.room_id "
            "WHERE q.id = %s AND r.expires_at > now() FOR UPDATE OF q",
            (question_id,),
        )
        row = await cur.fetchone()
    if row is None:
        raise ApiError(404, "question_not_found", "question not found")
    return row


@router.post("/rooms/{code}/questions", status_code=201)
async def create_question(code: str, body: QuestionIn, device: RequiredDevice, pool: Pool) -> dict:
    room = await load_room(pool, code)
    if room["closed_at"] is not None:
        raise ApiError(409, "room_closed", "this room is closed")
    limit = get_settings().questions_per_minute
    async with pool.connection() as conn:
        # One request per device at a time, so two quick posts cannot both pass the limit.
        await conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (str(device),))
        cur = await conn.execute(
            "SELECT count(*) FROM question WHERE device_id = %s "
            "AND created_at > now() - interval '1 minute'",
            (device,),
        )
        if (await cur.fetchone())[0] >= limit:
            raise ApiError(429, "rate_limited", f"max {limit} questions per minute")
        async with conn.cursor(row_factory=dict_row) as cur2:
            await cur2.execute(
                "INSERT INTO question (room_id, text, author_name, device_id) "
                "VALUES (%s, %s, %s, %s) "
                "RETURNING id, text, author_name, votes, status, created_at",
                (room["id"], body.text, body.author_name or None, device),
            )
            row = await cur2.fetchone()
        await events.notify(conn, room["code"], "question.created", row["id"])
    return question_json(row)


@router.post("/questions/{question_id}/vote")
async def toggle_vote(question_id: int, device: RequiredDevice, pool: Pool) -> dict:
    async with pool.connection() as conn:
        q = await _load_question_for_update(conn, question_id)
        if q["status"] == "hidden":
            raise ApiError(404, "question_not_found", "question not found")
        if q["room_closed"]:
            raise ApiError(409, "room_closed", "this room is closed")
        cur = await conn.execute(
            "INSERT INTO question_vote (question_id, device_id) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (question_id, device),
        )
        if cur.rowcount == 1:
            voted, delta = True, 1
        else:  # already voted: tapping again removes the vote
            await conn.execute(
                "DELETE FROM question_vote WHERE question_id = %s AND device_id = %s",
                (question_id, device),
            )
            voted, delta = False, -1
        # The counter changes in the same transaction as the vote row (and the notify).
        cur = await conn.execute(
            "UPDATE question SET votes = votes + %s WHERE id = %s RETURNING votes",
            (delta, question_id),
        )
        votes = (await cur.fetchone())[0]
        await events.notify(conn, q["room_code"], "question.updated", question_id)
    return {"id": question_id, "votes": votes, "voted": voted}


@router.patch("/questions/{question_id}")
async def moderate_question(
    question_id: int, body: QuestionPatch, pool: Pool, authorization: AuthHeader = None
) -> dict:
    async with pool.connection() as conn:
        q = await _load_question_for_update(conn, question_id)
        require_host_token({"host_token_hash": q["host_token_hash"]}, authorization)
        await conn.execute(
            "UPDATE question SET status = %s WHERE id = %s", (body.status, question_id)
        )
        await events.notify(conn, q["room_code"], "question.updated", question_id)
    return question_json({**q, "status": body.status})
