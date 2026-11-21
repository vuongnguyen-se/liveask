import psycopg
import pytest
from helpers import host, make_room, new_device


def make_poll(client, room, options=("EKS", "ECS", "Lambda"), open_it=False):
    r = client.post(
        f"/api/rooms/{room['code']}/polls",
        json={"question": "Which AWS service next?", "options": list(options)},
        headers=host(room["host_token"]),
    )
    assert r.status_code == 201
    poll = r.json()
    if open_it:
        set_status(client, room, poll["id"], "open")
    return poll


def set_status(client, room, poll_id, status):
    return client.patch(
        f"/api/polls/{poll_id}", json={"status": status}, headers=host(room["host_token"])
    )


def vote(client, poll_id, device, option):
    return client.post(f"/api/polls/{poll_id}/vote", json={"option_index": option}, headers=device)


def snapshot(client, room, headers=None):
    return client.get(f"/api/rooms/{room['code']}", headers=headers or {}).json()


def test_create_poll_starts_as_draft_with_zero_counts(client):
    room = make_room(client)
    poll = make_poll(client, room)
    assert poll["status"] == "draft"
    assert poll["options"] == ["EKS", "ECS", "Lambda"]
    assert poll["counts"] == [0, 0, 0] and poll["total"] == 0


@pytest.mark.parametrize(
    "body",
    [
        {"question": "", "options": ["a", "b"]},
        {"question": "q", "options": ["only one"]},
        {"question": "q", "options": [str(i) for i in range(7)]},
        {"question": "q", "options": ["a", " "]},
        {"question": "q", "options": ["a", "x" * 81]},
        {"question": "x" * 201, "options": ["a", "b"]},
    ],
)
def test_poll_input_is_validated(client, body):
    room = make_room(client)
    r = client.post(f"/api/rooms/{room['code']}/polls", json=body, headers=host(room["host_token"]))
    assert r.status_code == 422


def test_only_the_host_manages_polls(client):
    room = make_room(client)
    url = f"/api/rooms/{room['code']}/polls"
    body = {"question": "q", "options": ["a", "b"]}
    assert client.post(url, json=body).status_code == 401
    assert client.post(url, json=body, headers=host("wrong")).status_code == 403
    poll = make_poll(client, room)
    assert client.patch(f"/api/polls/{poll['id']}", json={"status": "open"}).status_code == 401
    other = make_room(client)
    assert set_status(client, other, poll["id"], "open").status_code == 403


def test_drafts_are_hidden_from_the_audience(client):
    room = make_room(client)
    poll = make_poll(client, room)
    assert snapshot(client, room)["polls"] == []
    assert [p["id"] for p in snapshot(client, room, host(room["host_token"]))["polls"]] == [
        poll["id"]
    ]
    assert vote(client, poll["id"], new_device(), 0).status_code == 404
    set_status(client, room, poll["id"], "open")
    assert [p["id"] for p in snapshot(client, room)["polls"]] == [poll["id"]]


def test_status_transitions(client):
    room = make_room(client)
    poll = make_poll(client, room)
    pid = poll["id"]
    assert set_status(client, room, pid, "closed").status_code == 409  # draft -> closed
    assert set_status(client, room, pid, "open").json()["status"] == "open"
    assert set_status(client, room, pid, "open").status_code == 200  # same status: no-op
    assert set_status(client, room, pid, "closed").json()["status"] == "closed"
    reopen = set_status(client, room, pid, "open")
    assert reopen.status_code == 409
    assert reopen.json()["error"]["code"] == "invalid_transition"


def test_voting_counts_and_changing_a_vote(client):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    a, b = new_device(), new_device()

    assert vote(client, pid, a, 1).json()["counts"] == [0, 1, 0]
    after_b = vote(client, pid, b, 1).json()
    assert after_b["counts"] == [0, 2, 0] and after_b["total"] == 2
    # a changes her mind: still one vote per device, now on option 2
    changed = vote(client, pid, a, 2).json()
    assert changed["counts"] == [0, 1, 1] and changed["total"] == 2
    # repeating the same vote changes nothing
    assert vote(client, pid, a, 2).json()["counts"] == [0, 1, 1]


def test_cannot_vote_for_a_missing_option(client):
    room = make_room(client)
    pid = make_poll(client, room, options=("a", "b"), open_it=True)["id"]
    assert vote(client, pid, new_device(), 2).status_code == 422
    assert vote(client, pid, new_device(), -1).status_code == 422
    assert vote(client, pid, new_device(), 99).status_code == 422


def test_cannot_vote_when_the_poll_is_closed(client):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    vote(client, pid, new_device(), 0)
    set_status(client, room, pid, "closed")
    r = vote(client, pid, new_device(), 0)
    assert r.status_code == 409 and r.json()["error"]["code"] == "poll_closed"
    assert snapshot(client, room)["polls"][0]["counts"] == [1, 0, 0]  # results stay visible


def test_vote_needs_a_device_id(client):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    r = client.post(f"/api/polls/{pid}/vote", json={"option_index": 0})
    assert r.status_code == 400


def test_snapshot_reports_my_poll_votes(client):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    me = new_device()
    vote(client, pid, me, 2)
    assert snapshot(client, room, me)["my_votes"]["polls"] == {str(pid): 2}
    assert snapshot(client, room, new_device())["my_votes"]["polls"] == {}


def test_closed_room_blocks_poll_changes(client):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    client.post(f"/api/rooms/{room['code']}/close", headers=host(room["host_token"]))
    assert vote(client, pid, new_device(), 0).status_code == 409
    assert set_status(client, room, pid, "closed").status_code == 409


def test_deleting_the_room_removes_polls_and_votes(client, db_url):
    room = make_room(client)
    pid = make_poll(client, room, open_it=True)["id"]
    vote(client, pid, new_device(), 0)
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("DELETE FROM room WHERE code = %s", (room["code"],))
        assert conn.execute("SELECT count(*) FROM poll").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM poll_vote").fetchone()[0] == 0
