"""Small helpers shared by the API tests."""

from __future__ import annotations

import uuid


def new_device() -> dict:
    return {"X-Device-Id": str(uuid.uuid4())}


def host(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_room(client, title: str = "Cloud 101") -> dict:
    r = client.post("/api/rooms", json={"title": title})
    assert r.status_code == 201
    return r.json()


def ask(client, code: str, device: dict, text: str = "What is a pod?", **extra):
    return client.post(f"/api/rooms/{code}/questions", json={"text": text, **extra}, headers=device)
