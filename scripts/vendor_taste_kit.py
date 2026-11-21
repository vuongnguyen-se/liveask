"""Copy the taste-skill kit files LiveAsk uses into app/liveask/static/assets/, unmodified.

    python scripts/vendor_taste_kit.py --skill "C:/Users/Vuong/Downloads/taste-skill/skills/taste-skill"
    python scripts/vendor_taste_kit.py --check        # verify the vendored files are untouched

The kit is never edited (D-018). MANIFEST.sha256 records the checksum of every vendored
file, and tests/test_kit.py fails if one of them changes. To use a new kit file, add it to
FILES, run this script with --skill, and commit the files and the manifest together.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "app" / "liveask" / "static" / "assets"
MANIFEST = DEST / "MANIFEST.sha256"

# Paths relative to the skill's assets/ folder. Keep sorted by folder.
FILES = [
    "system.css",
    "system.js",
    "ui/base.css",
    "ui/cards.css",
    "ui/ui.js",
    "motion/motion.css",
    "motion/motion.js",
    "layout/layout.css",
    "layout/layout.js",
    "icons/icon.css",
    "backgrounds/backgrounds.css",
    "backgrounds/backgrounds.js",
    "diagrams/diagram.css",
    "diagrams/diagram.js",
    "diagrams/mount.js",
    "diagrams/presets.json",
    "moments/moments.js",
    "moments/lib.js",
    "moments/marquee-row/moment.css",
    "moments/marquee-row/moment.js",
]


def lf(data: bytes) -> bytes:
    """Line endings as git stores them (LF). A Windows clone of the kit may have CRLF."""
    return data.replace(b"\r\n", b"\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(lf(path.read_bytes())).hexdigest()


def write_manifest() -> None:
    lines = [f"{sha256(DEST / name)}  {name}" for name in sorted(FILES)]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def check() -> int:
    bad = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = DEST / name
        if not path.exists() or sha256(path) != digest:
            bad.append(name)
    for name in bad:
        print("MODIFIED OR MISSING:", name)
    print("kit unmodified" if not bad else f"{len(bad)} file(s) differ from the manifest")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skill", help="path to the taste-skill folder (the one holding assets/)")
    parser.add_argument("--check", action="store_true", help="verify the vendored files")
    args = parser.parse_args()
    if args.check:
        return check()
    if not args.skill:
        parser.error("give --skill or --check")
    source = Path(args.skill) / "assets"
    for name in FILES:
        src = source / name
        if not src.exists():
            print("missing in the skill:", name)
            return 1
        target = DEST / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(lf(src.read_bytes()))  # unchanged apart from LF line endings
    licence = Path(args.skill).parent.parent / "LICENSE"
    if licence.exists():
        (DEST / "LICENSE-taste-skill").write_bytes(lf(licence.read_bytes()))
    write_manifest()
    print(f"vendored {len(FILES)} files into {DEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
