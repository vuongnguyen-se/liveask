import asyncio

import psycopg
import pytest
from fastapi.testclient import TestClient

from liveask import migrate, security
from liveask.main import app


@pytest.fixture
def client(monkeypatch, db_url):
    asyncio.run(migrate.run(db_url))
    monkeypatch.setenv("DATABASE_URL", db_url)
    with TestClient(app) as c:
        yield c


def make_room(client, title="Cloud 101"):
    r = client.post("/api/rooms", json={"title": title})
    assert r.status_code == 201
    return r.json()


def host(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_room(client):
    room = make_room(client, "  Cloud 101  ")
    assert len(room["code"]) == 6
    assert room["title"] == "Cloud 101"  # trimmed
    assert room["audience_url"] == f"/r/{room['code']}"
    assert room["screen_url"] == f"/screen/{room['code']}"
    assert room["host_url"] == f"/host/{room['code']}#t={room['host_token']}"
    assert len(room["host_token"]) == 43


@pytest.mark.parametrize("body", [{}, {"title": ""}, {"title": "   "}, {"title": "x" * 121}])
def test_create_room_validates_title(client, body):
    r = client.post("/api/rooms", json=body)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_get_room_snapshot(client):
    room = make_room(client)
    r = client.get(f"/api/rooms/{room['code']}")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == room["code"]
    assert body["closed"] is False
    assert body["questions"] == [] and body["polls"] == []
    assert "host_token" not in body
    # codes are case-insensitive for people typing them in
    assert client.get(f"/api/rooms/{room['code'].lower()}").status_code == 200


@pytest.mark.parametrize("code", ["ZZZZZZ", "abc", "NOT-A-CODE"])
def test_unknown_room_is_404(client, code):
    r = client.get(f"/api/rooms/{code}")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "room_not_found"


def test_token_is_not_stored_in_plain_text(client, db_url):
    room = make_room(client)
    with psycopg.connect(db_url) as conn:
        row = conn.execute("SELECT * FROM room WHERE code = %s", (room["code"],)).fetchone()
        stored = [str(v) for v in row]
        assert security.hash_token(room["host_token"]) in stored
        assert not any(room["host_token"] in v for v in stored)


def test_close_requires_the_right_token(client):
    room = make_room(client)
    url = f"/api/rooms/{room['code']}/close"
    assert client.post(url).status_code == 401
    wrong = client.post(url, headers=host("not-the-token"))
    assert wrong.status_code == 403
    assert wrong.json()["error"]["code"] == "forbidden"
    assert client.get(f"/api/rooms/{room['code']}").json()["closed"] is False


def test_close_room(client):
    room = make_room(client)
    url = f"/api/rooms/{room['code']}/close"
    assert client.post(url, headers=host(room["host_token"])).status_code == 204
    assert client.get(f"/api/rooms/{room['code']}").json()["closed"] is True
    # closing twice is harmless
    assert client.post(url, headers=host(room["host_token"])).status_code == 204


def test_one_rooms_token_does_not_open_another_room(client):
    a, b = make_room(client), make_room(client)
    r = client.post(f"/api/rooms/{b['code']}/close", headers=host(a["host_token"]))
    assert r.status_code == 403


def test_expired_room_is_gone(client, db_url):
    room = make_room(client)
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("UPDATE room SET expires_at = now() - interval '1 minute'")
    assert client.get(f"/api/rooms/{room['code']}").status_code == 404
