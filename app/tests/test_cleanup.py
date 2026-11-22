import psycopg
from helpers import ask, make_room, new_device

from liveask import cleanup


def counts(db_url):
    with psycopg.connect(db_url) as conn:
        return {
            table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("room", "question", "question_vote", "poll", "poll_vote")
        }


def test_only_expired_rooms_and_everything_under_them_are_deleted(client, db_url):
    keep = make_room(client, "Still running")
    gone = make_room(client, "Expired")
    q_keep = ask(client, keep["code"], new_device()).json()
    q_gone = ask(client, gone["code"], new_device()).json()
    client.post(f"/api/questions/{q_keep['id']}/vote", headers=new_device())
    client.post(f"/api/questions/{q_gone['id']}/vote", headers=new_device())
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute(
            "UPDATE room SET expires_at = now() - interval '1 minute' WHERE code = %s",
            (gone["code"],),
        )
    assert counts(db_url)["room"] == 2

    import asyncio

    assert asyncio.run(cleanup.run(db_url)) == 1

    after = counts(db_url)
    assert after == {"room": 1, "question": 1, "question_vote": 1, "poll": 0, "poll_vote": 0}
    assert client.get(f"/api/rooms/{keep['code']}").status_code == 200


def test_running_it_again_is_harmless(client, db_url):
    import asyncio

    make_room(client)
    assert asyncio.run(cleanup.run(db_url)) == 0
    assert asyncio.run(cleanup.run(db_url)) == 0
    assert counts(db_url)["room"] == 1
