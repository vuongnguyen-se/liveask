from fastapi.testclient import TestClient

from liveask.main import app


def test_healthz_never_needs_the_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        assert c.get("/healthz").json() == {"status": "ok"}


def test_readyz_is_503_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        assert c.get("/readyz").status_code == 503


def test_readyz_is_ready_with_a_database(monkeypatch, db_url):
    monkeypatch.setenv("DATABASE_URL", db_url)
    with TestClient(app) as c:
        assert c.get("/readyz").json() == {"status": "ready"}


def test_burn_is_bounded(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as c:
        assert c.get("/burn?ms=5").json()["iterations"] > 0
