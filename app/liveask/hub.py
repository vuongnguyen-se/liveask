"""WebSocket hub: pushes database events to the clients connected to THIS pod.

Every pod keeps one dedicated connection running ``LISTEN liveask_events``. A write on any
pod ends with ``pg_notify`` (see events.py), so every pod hears about it after the commit,
loads the changed object and sends it to its own WebSocket clients in that room. That is
how a phone on pod A sees a question posted through pod B, with no sticky sessions.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

import psycopg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from psycopg_pool import AsyncConnectionPool

from liveask import events, polls, questions
from liveask.common import load_room
from liveask.errors import ApiError

log = logging.getLogger("liveask.hub")

SEND_TIMEOUT = 5  # seconds; a client that cannot take a message in time is dropped
RECONNECT_DELAY = 1

router = APIRouter()


class Hub:
    def __init__(self, url: str, pool: AsyncConnectionPool, pod: str, max_per_room: int) -> None:
        self.url = url
        self.pool = pool
        self.pod = pod
        self.max_per_room = max_per_room
        self.rooms: dict[str, set[WebSocket]] = {}
        self.listening = False  # /readyz reports not-ready while this is False
        self.shutting_down = False
        self._task: asyncio.Task | None = None
        self._ready = asyncio.Event()

    # --- lifecycle -------------------------------------------------------------------

    async def start(self) -> None:
        self._task = asyncio.create_task(self._listen_forever(), name="hub-listener")
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._ready.wait(), timeout=10)

    async def stop(self) -> None:
        """Tell clients to reconnect elsewhere (1012 = service restart) and stop listening."""
        self.shutting_down = True
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        sockets = [ws for group in self.rooms.values() for ws in group]
        await asyncio.gather(*(self._close(ws, 1012) for ws in sockets), return_exceptions=True)
        self.rooms.clear()

    @staticmethod
    async def _close(ws: WebSocket, code: int) -> None:
        with contextlib.suppress(Exception):
            await asyncio.wait_for(ws.close(code=code), timeout=2)

    # --- connections -----------------------------------------------------------------

    def add(self, code: str, ws: WebSocket) -> bool:
        group = self.rooms.setdefault(code, set())
        if len(group) >= self.max_per_room:
            return False
        group.add(ws)
        return True

    def remove(self, code: str, ws: WebSocket) -> None:
        group = self.rooms.get(code)
        if group is not None:
            group.discard(ws)
            if not group:
                del self.rooms[code]

    def connection_count(self) -> int:
        return sum(len(g) for g in self.rooms.values())

    # --- sending ---------------------------------------------------------------------

    @staticmethod
    async def _send(ws: WebSocket, message: dict) -> bool:
        try:
            await asyncio.wait_for(ws.send_json(message), timeout=SEND_TIMEOUT)
            return True
        except Exception:  # disconnected, too slow, or already closed
            return False

    async def broadcast(self, code: str, message: dict) -> None:
        clients = list(self.rooms.get(code, ()))
        results = await asyncio.gather(*(self._send(ws, message) for ws in clients))
        for ws, ok in zip(clients, results, strict=True):
            if not ok:  # dead socket: forget it so it cannot leak
                self.remove(code, ws)
                await self._close(ws, 1011)

    async def broadcast_all(self, message: dict) -> None:
        for code in list(self.rooms):
            await self.broadcast(code, message)

    # --- listening -------------------------------------------------------------------

    async def _listen_forever(self) -> None:
        first = True
        while True:
            try:
                async with await psycopg.AsyncConnection.connect(
                    self.url,
                    autocommit=True,
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                ) as conn:
                    await conn.execute(f"LISTEN {events.CHANNEL}")
                    self.listening = True
                    self._ready.set()
                    log.info("listening on %s", events.CHANNEL)
                    if not first:
                        # Events may have been missed while we were disconnected.
                        await self.broadcast_all({"type": "resync", "data": {}})
                    first = False
                    async for notice in conn.notifies():
                        await self._handle(notice.payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("LISTEN connection lost; retrying in %ss", RECONNECT_DELAY)
            finally:
                self.listening = False
            await asyncio.sleep(RECONNECT_DELAY)

    async def _handle(self, payload: str) -> None:
        try:
            event = json.loads(payload)
            code = event["room"]
            if code not in self.rooms:  # nobody here is in that room: skip the DB read
                return
            message = await self._build_message(event)
            if message is not None:
                await self.broadcast(code, message)
        except Exception:
            log.exception("could not handle event %r", payload)

    async def _build_message(self, event: dict) -> dict | None:
        type_ = event["type"]
        if type_ == "room.closed":
            return {"type": type_, "data": {}}
        async with self.pool.connection() as conn:
            if type_.startswith("question."):
                q = await questions.question_by_id(conn, event["id"])
                if q is None:
                    return None
                if q["status"] == "hidden":
                    # Never push the text of a hidden question; clients just remove it.
                    return {"type": "question.updated", "data": {"id": q["id"], "status": "hidden"}}
                return {"type": type_, "data": q}
            if type_.startswith("poll."):
                poll = await polls.poll_by_id(conn, event["id"])
                return None if poll is None else {"type": type_, "data": poll}
        return None


@router.websocket("/ws/rooms/{code}")
async def room_socket(ws: WebSocket, code: str, role: str = "audience") -> None:
    hub: Hub | None = ws.app.state.hub
    await ws.accept()
    if hub is None or hub.shutting_down:
        await ws.close(code=1013)  # try again later
        return
    try:
        room = await load_room(ws.app.state.pool, code)
    except ApiError:
        await ws.close(code=4404)  # unknown or expired room: do not retry
        return
    room_code = room["code"]
    if not hub.add(room_code, ws):
        await ws.close(code=1013)  # room is at its connection limit on this pod
        return
    log.info("ws connected room=%s role=%s", room_code, role[:10])
    try:
        await ws.send_json({"type": "hello", "data": {"pod": hub.pod}})
        while True:
            try:
                message = json.loads(await ws.receive_text())
            except ValueError:
                continue
            if isinstance(message, dict) and message.get("type") == "ping":
                await ws.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(room_code, ws)
