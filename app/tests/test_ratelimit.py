"""Room creation is limited per network address, in memory, on both entry points."""

import psycopg
import pytest
from helpers import make_room

from liveask import ratelimit
from liveask.ratelimit import SlidingWindow

# --- the window itself (no database) -------------------------------------------------------


def test_the_window_allows_up_to_the_limit_then_says_how_long_to_wait():
    w = SlidingWindow()
    assert [w.retry_after("a", 3, 100, now=t) for t in (0, 10, 20)] == [0, 0, 0]
    assert w.retry_after("a", 3, 100, now=30) == 71  # the first hit leaves the window at t=100


def test_a_rejected_try_does_not_extend_the_wait():
    w = SlidingWindow()
    for t in (0, 1):
        w.retry_after("a", 2, 100, now=t)
    first = w.retry_after("a", 2, 100, now=50)
    assert w.retry_after("a", 2, 100, now=60) == first - 10  # still counting down from t=0


def test_hits_expire_and_addresses_are_counted_separately():
    w = SlidingWindow()
    assert w.retry_after("a", 1, 100, now=0) == 0
    assert w.retry_after("a", 1, 100, now=1) > 0
    assert w.retry_after("b", 1, 100, now=1) == 0
    assert w.retry_after("a", 1, 100, now=100) == 0  # the first hit is a full window old


def test_the_table_is_swept_when_it_grows_too_large(monkeypatch):
    monkeypatch.setattr(ratelimit, "SWEEP_ABOVE", 5)
    w = SlidingWindow()
    for i in range(10):
        w.retry_after(f"ip{i}", 1, 100, now=0)
    w.retry_after("new", 1, 100, now=500)  # all earlier hits are expired now
    assert list(w._hits) == ["new"]


# --- the API -------------------------------------------------------------------------------


def post_room(client, **headers):
    return client.post("/api/rooms", json={"title": "Cloud 101"}, headers=headers)


def post_form(client, **headers):
    return client.post(
        "/create", data={"title": "Cloud 101"}, headers=headers, follow_redirects=False
    )


def room_count(db_url):
    with psycopg.connect(db_url) as conn:
        return conn.execute("SELECT count(*) FROM room").fetchone()[0]


@pytest.fixture
def two_per_hour(monkeypatch):
    monkeypatch.setenv("ROOMS_PER_HOUR_PER_IP", "2")


def test_the_api_stops_the_third_room_with_a_429(client, two_per_hour, db_url):
    assert [post_room(client).status_code for _ in range(2)] == [201, 201]
    r = post_room(client)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert room_count(db_url) == 2


def test_the_form_gets_a_plain_429_with_retry_after_and_creates_nothing(
    client, two_per_hour, db_url
):
    assert [post_form(client).status_code for _ in range(2)] == [303, 303]
    r = post_form(client)
    assert r.status_code == 429 and "Too many rooms" in r.text
    assert 1 <= int(r.headers["retry-after"]) <= 3600
    assert room_count(db_url) == 2


def test_both_entry_points_share_one_count(client, two_per_hour):
    assert post_room(client).status_code == 201
    assert post_form(client).status_code == 303
    assert post_room(client).status_code == 429


def test_other_calls_are_not_limited(client, two_per_hour):
    code = make_room(client)["code"]
    make_room(client)
    for _ in range(5):
        assert client.get(f"/api/rooms/{code}").status_code == 200


def test_the_proxy_header_picks_the_address_and_a_forged_entry_is_ignored(client, two_per_hour):
    one = {"X-Forwarded-For": "10.0.0.1"}
    assert [post_room(client, **one).status_code for _ in range(2)] == [201, 201]
    assert post_room(client, **one).status_code == 429
    assert post_room(client, **{"X-Forwarded-For": "10.0.0.2"}).status_code == 201  # another caller
    # the caller prepends fake entries; the proxy's own entry on the right still identifies them
    for fake in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        r = post_room(client, **{"X-Forwarded-For": f"{fake}, 10.0.0.1"})
        assert r.status_code == 429


def test_zero_proxy_hops_ignores_the_header(client, two_per_hour, monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_HOPS", "0")
    assert [
        post_room(client, **{"X-Forwarded-For": f"9.9.9.{i}"}).status_code for i in range(2)
    ] == [201, 201]
    assert post_room(client, **{"X-Forwarded-For": "9.9.9.99"}).status_code == 429


def test_a_limit_of_zero_turns_it_off(client, monkeypatch):
    monkeypatch.setenv("ROOMS_PER_HOUR_PER_IP", "0")
    assert all(post_room(client).status_code == 201 for _ in range(30))
