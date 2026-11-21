from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liveask.main import STATIC_DIR, app


@pytest.fixture
def web(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)  # pages need no database
    with TestClient(app) as c:
        yield c


@pytest.mark.parametrize(
    ("path", "view"),
    [
        ("/", "index"),
        ("/r/K7PX4M", "audience"),
        ("/host/K7PX4M", "host"),
        ("/screen/K7PX4M", "screen"),
    ],
)
def test_pages_are_served(web, path, view):
    r = web.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert f'data-view="{view}"' in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_static_files_are_served(web):
    for name in ("app.js", "styles.css", "qrcode.js"):
        assert web.get(f"/static/{name}").status_code == 200


def test_host_token_fragment_never_reaches_the_server(web):
    # The #fragment is stripped by the browser; the page must work without any token in the path.
    assert web.get("/host/K7PX4M").status_code == 200


def test_pages_load_no_external_resources():
    for page in STATIC_DIR.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, page.name


def test_front_end_never_uses_innerhtml():
    # User text must go through textContent, so a question cannot inject markup.
    own_code = ["app.js"] + [p.name for p in STATIC_DIR.glob("*.html")]
    for name in own_code:
        text = (STATIC_DIR / name).read_text(encoding="utf-8")
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            assert banned not in text, f"{banned} found in {name}"
    assert Path(STATIC_DIR / "qrcode.js").exists()
