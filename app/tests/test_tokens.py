"""The design tokens stay as the dealer printed them (docs/ui/DESIGN_PLAN.md)."""

import re

from fastapi.testclient import TestClient

from liveask.main import STATIC_DIR, app

DEALT = {
    "--p-bg": "#f7f9fa",
    "--p-surface": "#ecf0f2",
    "--p-ink": "#1f3038",
    "--p-muted": "#5d6b72",
    "--p-accent": "#0d7480",
    "--p-accent-ink": "#ffffff",
    "--p-action": "#0d7480",
    "--p-action-ink": "#ffffff",
    "--p-inv-bg": "#1f3038",
    "--p-inv-surface": "#2c3c44",
    "--p-inv-ink": "#f7f9fa",
    "--p-inv-muted": "#9ea7ab",
    "--p-inv-accent": "#f7f9fa",
    "--p-inv-accent-ink": "#1f3038",
    "--p-inv-action": "#f7f9fa",
    "--p-inv-action-ink": "#1f3038",
    "--display-weight": "500",
    "--display-tracking": "-0.035em",
    "--display-tracking-xl": "-0.04em",
}


def tokens() -> dict[str, str]:
    css = (STATIC_DIR / "tokens.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+):\s*([^;]+);", css)}


def test_color_and_display_tokens_are_the_dealt_ones():
    found = tokens()
    for name, value in DEALT.items():
        assert found.get(name) == value, f"{name} drifted from the deal"


def test_both_dealt_faces_are_named_with_a_fallback():
    found = tokens()
    assert found["--font-display"].startswith('"Host Grotesk"')
    assert found["--font-text"].startswith('"Host Grotesk"')
    assert found["--font-mono"].startswith('"JetBrains Mono"')
    assert "system-ui" in found["--font-display"]


def test_tokens_are_served(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as web:
        assert web.get("/static/tokens.css").status_code == 200
