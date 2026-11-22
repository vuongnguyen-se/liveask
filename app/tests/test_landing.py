"""The landing page's forms: plain HTML posts that must work with no JavaScript."""

import re

import psycopg
from helpers import host


def create(client, title="Cloud 101"):
    return client.post("/create", data={"title": title}, follow_redirects=False)


def room_count(db_url):
    with psycopg.connect(db_url) as conn:
        return conn.execute("SELECT count(*) FROM room").fetchone()[0]


def test_create_redirects_to_the_host_page_with_the_token_in_the_fragment(client):
    r = create(client, "  Cloud 101  ")
    assert r.status_code == 303
    match = re.fullmatch(r"/host/([A-Z0-9]{6})#t=([\w-]{43})", r.headers["location"])
    assert match, r.headers["location"]
    code, token = match.groups()
    # the page behind it is a real room, owned by that token
    assert client.get(f"/api/rooms/{code}").json()["title"] == "Cloud 101"
    assert client.post(f"/api/rooms/{code}/close", headers=host(token)).status_code == 204


def test_create_keeps_unicode_titles(client):
    found = re.search(r"/host/([A-Z0-9]{6})", create(client, "Bài giảng Cloud").headers["location"])
    assert client.get(f"/api/rooms/{found.group(1)}").json()["title"] == "Bài giảng Cloud"


def test_a_bad_title_goes_back_to_the_form_and_creates_nothing(client, db_url):
    for title in ("", "   ", "x" * 121):
        r = create(client, title)
        assert r.status_code == 303 and r.headers["location"] == "/#create"
    assert room_count(db_url) == 0


def test_create_ignores_anything_but_a_small_form_post(client, db_url):
    r = client.post("/create", json={"title": "Cloud 101"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/#create"
    assert create(client, "x" * 5000).headers["location"] == "/#create"
    assert room_count(db_url) == 0


def test_join_goes_to_the_audience_page_whatever_the_case(client):
    for code in ("K7PX4M", "k7px4m", " k7px4m "):
        r = client.get("/join", params={"code": code}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/r/K7PX4M"


def test_a_malformed_code_goes_back_to_the_join_form(client):
    for code in ("", "abc", "K7PX4M7", "K7P-4M", "../etc"):
        r = client.get("/join", params={"code": code}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/#join"
    assert client.get("/join", follow_redirects=False).headers["location"] == "/#join"
