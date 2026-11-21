from fastapi.testclient import TestClient

from main import app


def client() -> TestClient:
    return TestClient(app)


def test_health_and_ready():
    with client() as c:
        assert c.get("/healthz").json() == {"status": "ok"}
        assert c.get("/readyz").json() == {"status": "ready"}


def test_info_reports_memory_store_without_database():
    with client() as c:
        body = c.get("/").json()
        assert body["service"] == "notes-api"
        assert body["storage"] == "MemoryStore"


def test_create_and_list_notes():
    with client() as c:
        created = c.post("/notes", json={"text": "  hello eks  "})
        assert created.status_code == 201
        assert created.json()["text"] == "hello eks"
        notes = c.get("/notes").json()
        assert notes[0]["text"] == "hello eks"


def test_rejects_empty_note():
    with client() as c:
        assert c.post("/notes", json={"text": ""}).status_code == 422


def test_burn_is_bounded():
    with client() as c:
        assert c.get("/burn", params={"ms": 5}).status_code == 200
