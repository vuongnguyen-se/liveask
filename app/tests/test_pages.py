import re
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
    ("path", "marker"),
    [
        ("/", 'data-type="software"'),  # the landing page
        ("/r/K7PX4M", 'data-view="audience"'),
        ("/host/K7PX4M", 'data-view="host"'),
        ("/screen/K7PX4M", 'data-view="screen"'),
    ],
)
def test_pages_are_served(web, path, marker):
    r = web.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert marker in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_static_files_are_served(web):
    for name in ("app.js", "styles.css", "qrcode.js"):
        assert web.get(f"/static/{name}").status_code == 200


def test_host_token_fragment_never_reaches_the_server(web):
    # The #fragment is stripped by the browser; the page must work without any token in the path.
    assert web.get("/host/K7PX4M").status_code == 200


REMOTE_RESOURCE = re.compile(
    r"<(?:link|script|img|iframe|source|video|audio)[^>]*?(?:href|src)=[\"'](?:https?:)?//",
    re.IGNORECASE,
)


def test_pages_load_no_external_resources():
    # A link to another site (the source code) is fine; loading anything from one is not.
    for page in STATIC_DIR.glob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert not REMOTE_RESOURCE.search(text), f"{page.name} loads a remote resource"
    for sheet in ("tokens.css", "styles.css", "landing.css", "fonts/fonts.css"):
        css = (STATIC_DIR / sheet).read_text(encoding="utf-8")
        assert not re.search(r"url\(\s*[\"']?(?:https?:)?//", css), f"{sheet} loads a remote file"


def test_front_end_never_uses_innerhtml():
    # User text must go through textContent, so a question cannot inject markup.
    own_code = ["app.js"] + [p.name for p in STATIC_DIR.glob("*.html")]
    for name in own_code:
        text = (STATIC_DIR / name).read_text(encoding="utf-8")
        for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            assert banned not in text, f"{banned} found in {name}"
    assert Path(STATIC_DIR / "qrcode.js").exists()
