"""D-017: fonts are self-hosted. No page or stylesheet may load them from another site."""

import re

from fastapi.testclient import TestClient

from liveask.main import STATIC_DIR, app

FONTS = STATIC_DIR / "fonts"


def test_every_font_face_points_to_a_real_local_woff2_file():
    css = (FONTS / "fonts.css").read_text(encoding="utf-8")
    urls = re.findall(r'url\("([^"]+)"\)', css)
    assert urls, "no @font-face rules"
    for url in urls:
        assert "://" not in url, f"{url} is remote"
        assert (FONTS / url).read_bytes()[:4] == b"wOF2", f"{url} is not a woff2 file"
    assert css.count("font-display: swap") == css.count("@font-face")


def test_at_most_four_font_files_and_each_family_has_its_licence():
    assert len(list(FONTS.glob("*.woff2"))) <= 4  # the skill's limit (system.md, layout-v4 5)
    for licence in ("OFL-HostGrotesk.txt", "OFL-JetBrainsMono.txt"):
        assert "SIL OPEN FONT LICENSE" in (FONTS / licence).read_text(encoding="utf-8").upper()


def test_nothing_we_serve_names_a_font_host():
    for path in STATIC_DIR.rglob("*"):
        if path.suffix in {".html", ".css", ".js"} and "assets" not in path.parts:
            text = path.read_text(encoding="utf-8")
            assert "fonts.googleapis.com" not in text, path
            assert "fonts.gstatic.com" not in text, path


def test_fonts_are_served(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as web:
        assert web.get("/static/fonts/fonts.css").status_code == 200
        font = web.get("/static/fonts/host-grotesk-latin.woff2")
        assert font.status_code == 200 and font.content[:4] == b"wOF2"
