"""D-018: the vendored taste-skill kit stays unmodified and makes no external requests."""

import hashlib
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from liveask.main import STATIC_DIR, app

ASSETS = STATIC_DIR / "assets"
MANIFEST = ASSETS / "MANIFEST.sha256"
NOT_IN_MANIFEST = {"MANIFEST.sha256", "LICENSE-taste-skill"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def manifest() -> dict[str, str]:
    entries = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        checksum, name = line.split("  ", 1)
        entries[name] = checksum
    return entries


def test_every_kit_file_matches_its_checksum():
    changed = [name for name, checksum in manifest().items() if digest(ASSETS / name) != checksum]
    assert not changed, f"kit files were edited (never edit the kit, D-018): {changed}"


def test_no_unlisted_files_hide_in_the_kit_folder():
    on_disk = {
        p.relative_to(ASSETS).as_posix()
        for p in ASSETS.rglob("*")
        if p.is_file() and p.name not in NOT_IN_MANIFEST
    }
    assert on_disk == set(manifest()), "add new kit files through scripts/vendor_taste_kit.py"


def test_the_licence_travels_with_the_kit():
    assert "MIT License" in (ASSETS / "LICENSE-taste-skill").read_text(encoding="utf-8")


def test_the_kit_requests_nothing_from_another_site():
    # Comments may show example links and xmlns strings in SVG data are namespaces: neither
    # is a request, so only code is scanned.
    offending = []
    for name in manifest():
        text = (ASSETS / name).read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        for url in re.findall(r"https?://[^\s\"'`)<>]+", text):
            if not url.startswith(("http://www.w3.org/", "https://www.w3.org/")):
                offending.append(f"{name}: {url}")
    assert not offending, offending


@pytest.mark.parametrize(
    "name", ["system.css", "system.js", "layout/layout.css", "motion/motion.js"]
)
def test_kit_files_are_served(monkeypatch, name):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as web:
        response = web.get(f"/static/assets/{name}")
        assert response.status_code == 200
        assert len(response.content) > 1000
