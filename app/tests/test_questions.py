import psycopg
import pytest
from helpers import ask, host, make_room, new_device


def snapshot(client, room, headers=None):
    r = client.get(f"/api/rooms/{room['code']}", headers=headers or {})
    assert r.status_code == 200
    return r.json()


def test_post_question_appears_in_snapshot(client):
    room = make_room(client)
    r = ask(client, room["code"], new_device(), "  What is a pod?  ", author_name="Lan")
    assert r.status_code == 201
    q = r.json()
    assert q["text"] == "What is a pod?"
    assert q["author_name"] == "Lan"
    assert q["votes"] == 0 and q["status"] == "open"
    assert [x["id"] for x in snapshot(client, room)["questions"]] == [q["id"]]


@pytest.mark.parametrize(
    "extra",
    [{"text": ""}, {"text": "   "}, {"text": "x" * 281}, {"text": "ok", "author_name": "n" * 41}],
)
def test_question_input_is_validated(client, extra):
    room = make_room(client)
    r = client.post(f"/api/rooms/{room['code']}/questions", json=extra, headers=new_device())
    assert r.status_code == 422


def test_device_id_is_required_and_must_be_a_uuid(client):
    room = make_room(client)
    url = f"/api/rooms/{room['code']}/questions"
    assert client.post(url, json={"text": "hi"}).status_code == 400
    bad = client.post(url, json={"text": "hi"}, headers={"X-Device-Id": "nope"})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "invalid_device_id"


def test_rate_limit_is_five_per_minute_per_device(client):
    room = make_room(client)
    me, other = new_device(), new_device()
    for i in range(5):
        assert ask(client, room["code"], me, f"q{i}").status_code == 201
    blocked = ask(client, room["code"], me, "one too many")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert ask(client, room["code"], other, "different device").status_code == 201


def test_cannot_ask_in_a_closed_room(client):
    room = make_room(client)
    client.post(f"/api/rooms/{room['code']}/close", headers=host(room["host_token"]))
    assert ask(client, room["code"], new_device()).status_code == 409


def test_one_vote_per_device_and_tapping_again_removes_it(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    a, b = new_device(), new_device()
    url = f"/api/questions/{q['id']}/vote"

    assert client.post(url, headers=a).json() == {"id": q["id"], "votes": 1, "voted": True}
    assert client.post(url, headers=b).json()["votes"] == 2
    # same device again = unvote, never a second vote
    assert client.post(url, headers=a).json() == {"id": q["id"], "votes": 1, "voted": False}
    assert client.post(url, headers=a).json()["votes"] == 2


def test_vote_counter_matches_vote_rows(client, db_url):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    devices = [new_device() for _ in range(3)]
    for d in devices:
        client.post(f"/api/questions/{q['id']}/vote", headers=d)
    client.post(f"/api/questions/{q['id']}/vote", headers=devices[0])  # unvote
    with psycopg.connect(db_url) as conn:
        votes = conn.execute("SELECT votes FROM question WHERE id = %s", (q["id"],)).fetchone()[0]
        rows = conn.execute(
            "SELECT count(*) FROM question_vote WHERE question_id = %s", (q["id"],)
        ).fetchone()[0]
    assert votes == rows == 2


def test_snapshot_is_sorted_by_votes_then_newest(client):
    room = make_room(client)
    ids = [ask(client, room["code"], new_device(), f"q{i}").json()["id"] for i in range(3)]
    client.post(f"/api/questions/{ids[0]}/vote", headers=new_device())  # oldest gets a vote
    order = [q["id"] for q in snapshot(client, room)["questions"]]
    assert order == [ids[0], ids[2], ids[1]]  # votes first, then newest first


def test_my_votes_reflect_the_calling_device(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    me, other = new_device(), new_device()
    client.post(f"/api/questions/{q['id']}/vote", headers=me)
    assert snapshot(client, room, me)["my_votes"]["questions"] == [q["id"]]
    assert snapshot(client, room, other)["my_votes"]["questions"] == []
    assert snapshot(client, room)["my_votes"]["questions"] == []


def test_moderation_needs_the_host_token(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    url = f"/api/questions/{q['id']}"
    assert client.patch(url, json={"status": "hidden"}).status_code == 401
    assert client.patch(url, json={"status": "hidden"}, headers=host("wrong")).status_code == 403
    other_room = make_room(client)
    other = client.patch(url, json={"status": "hidden"}, headers=host(other_room["host_token"]))
    assert other.status_code == 403
    assert (
        client.patch(url, json={"status": "bogus"}, headers=host(room["host_token"])).status_code
        == 422
    )


def test_hidden_questions_are_invisible_to_the_audience_but_not_the_host(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    r = client.patch(
        f"/api/questions/{q['id']}", json={"status": "hidden"}, headers=host(room["host_token"])
    )
    assert r.status_code == 200 and r.json()["status"] == "hidden"

    assert snapshot(client, room)["questions"] == []
    seen_by_host = snapshot(client, room, host(room["host_token"]))["questions"]
    assert [x["id"] for x in seen_by_host] == [q["id"]]
    # nobody in the audience can vote on it either
    assert client.post(f"/api/questions/{q['id']}/vote", headers=new_device()).status_code == 404

    client.patch(
        f"/api/questions/{q['id']}", json={"status": "open"}, headers=host(room["host_token"])
    )
    assert len(snapshot(client, room)["questions"]) == 1


def test_answered_questions_stay_visible(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    client.patch(
        f"/api/questions/{q['id']}", json={"status": "answered"}, headers=host(room["host_token"])
    )
    assert snapshot(client, room)["questions"][0]["status"] == "answered"


def test_unknown_question_is_404(client):
    assert client.post("/api/questions/999999/vote", headers=new_device()).status_code == 404


def test_cannot_vote_in_a_closed_room(client):
    room = make_room(client)
    q = ask(client, room["code"], new_device()).json()
    client.post(f"/api/rooms/{room['code']}/close", headers=host(room["host_token"]))
    assert client.post(f"/api/questions/{q['id']}/vote", headers=new_device()).status_code == 409
