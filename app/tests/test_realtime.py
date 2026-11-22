"""The key test: two separate app processes ("pods") sharing one PostgreSQL.

A write sent to pod A must reach a WebSocket connected to pod B, because both pods
LISTEN to the same Postgres channel.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import uuid
from pathlib import Path

import httpx
import pytest
from websockets.asyncio.client import connect

from liveask import migrate

APP_DIR = Path(__file__).resolve().parent.parent


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Pod:
    def __init__(self, name: str, db_url: str, log_dir: Path) -> None:
        self.name = name
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.log_path = log_dir / f"{name}.log"
        env = {**os.environ, "DATABASE_URL": db_url, "POD_NAME": name}
        self._log = open(self.log_path, "w")  # noqa: SIM115 - closed in stop()
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "liveask.run", "--port", str(self.port)],
            cwd=APP_DIR,
            env=env,
            stdout=self._log,
            stderr=subprocess.STDOUT,
        )

    async def wait_ready(self, seconds: float = 20) -> None:
        async with httpx.AsyncClient() as http:
            for _ in range(int(seconds * 10)):
                if self.proc.poll() is not None:
                    break
                try:
                    if (await http.get(f"{self.base}/readyz")).status_code == 200:
                        return
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.1)
        raise AssertionError(f"{self.name} did not become ready:\n{self.log_path.read_text()}")

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self._log.close()


async def next_message(ws, type_: str, timeout: float = 5) -> dict:
    """Wait for the next message of this type (ignoring others such as hello)."""

    async def loop() -> dict:
        while True:
            message = json.loads(await ws.recv())
            if message["type"] == type_:
                return message

    try:
        return await asyncio.wait_for(loop(), timeout)
    except TimeoutError:
        raise AssertionError(f"no {type_!r} message within {timeout}s") from None


@pytest.fixture
async def pods(db_url, tmp_path):
    await migrate.run(db_url)
    pod_a, pod_b = Pod("pod-a", db_url, tmp_path), Pod("pod-b", db_url, tmp_path)
    try:
        await asyncio.gather(pod_a.wait_ready(), pod_b.wait_ready())
        yield pod_a, pod_b
    finally:
        pod_a.stop()
        pod_b.stop()


async def test_events_posted_to_pod_a_reach_a_websocket_on_pod_b(pods):
    a, b = pods
    device = {"X-Device-Id": str(uuid.uuid4())}
    async with httpx.AsyncClient(base_url=a.base) as http:
        room = (await http.post("/api/rooms", json={"title": "Two pods"})).json()
        code = room["code"]
        host = {"Authorization": f"Bearer {room['host_token']}"}

        async with connect(f"ws://127.0.0.1:{b.port}/ws/rooms/{code}?role=screen") as ws:
            hello = json.loads(await ws.recv())
            assert hello == {"type": "hello", "data": {"pod": "pod-b"}}  # we are on pod B

            # 1. a new question, posted through pod A
            r = await http.post(
                f"/api/rooms/{code}/questions", json={"text": "Why Kubernetes?"}, headers=device
            )
            qid = r.json()["id"]
            created = await next_message(ws, "question.created")
            assert created["data"]["text"] == "Why Kubernetes?"
            assert created["data"]["id"] == qid

            # 2. an upvote
            await http.post(f"/api/questions/{qid}/vote", headers=device)
            updated = await next_message(ws, "question.updated")
            assert updated["data"]["votes"] == 1

            # 3. moderation: a hidden question's text is never pushed to the audience
            await http.patch(f"/api/questions/{qid}", json={"status": "hidden"}, headers=host)
            hidden = await next_message(ws, "question.updated")
            assert hidden["data"] == {"id": qid, "status": "hidden"}

            # 4. polls: opening announces it, voting updates the counts
            poll = (
                await http.post(
                    f"/api/rooms/{code}/polls",
                    json={"question": "Next?", "options": ["EKS", "ECS"]},
                    headers=host,
                )
            ).json()
            await http.patch(f"/api/polls/{poll['id']}", json={"status": "open"}, headers=host)
            opened = await next_message(ws, "poll.created")
            assert opened["data"]["status"] == "open"
            await http.post(
                f"/api/polls/{poll['id']}/vote", json={"option_index": 1}, headers=device
            )
            counts = await next_message(ws, "poll.updated")
            assert counts["data"]["counts"] == [0, 1]

            # 5. closing the room
            await http.post(f"/api/rooms/{code}/close", headers=host)
            assert (await next_message(ws, "room.closed"))["data"] == {}


async def test_data_lives_in_postgres_so_it_survives_a_pod_stopping(pods):
    a, b = pods
    async with httpx.AsyncClient(base_url=a.base) as http:
        room = (await http.post("/api/rooms", json={"title": "Restart"})).json()
        code = room["code"]
        device = {"X-Device-Id": str(uuid.uuid4())}
        await http.post(f"/api/rooms/{code}/questions", json={"text": "survive?"}, headers=device)

    b.stop()  # pod B goes away; the question lives in Postgres, not in a pod
    async with httpx.AsyncClient(base_url=a.base) as http:
        snapshot = (await http.get(f"/api/rooms/{code}")).json()
    assert [q["text"] for q in snapshot["questions"]] == ["survive?"]
