# The vendored taste-skill kit

`app/liveask/static/assets/` holds the part of the [taste-skill](https://github.com/Leonxlnx/taste-skill) kit (version 2.5.1, MIT, licence in `LICENSE-taste-skill`) that LiveAsk's pages load: 20 files, about 450 KB of text (the whole skill is 39 MB). Decision D-018.

- **Unmodified.** The files are the skill's own, with LF line endings (the repository stores LF). `MANIFEST.sha256` lists the checksum of every file and `tests/test_kit.py` fails if one changes. To change how the kit looks, use the tokens and our own CSS, never the kit's files.
- **Add a file:** put its path in `FILES` in `scripts/vendor_taste_kit.py`, run
  `python scripts/vendor_taste_kit.py --skill "<path to taste-skill/skills/taste-skill>"`, and commit the file and the manifest together.
- **Check:** `python scripts/vendor_taste_kit.py --check`.
- **Why `innerHTML` appears in it:** `system.js`, `motion.js` and `ui.js` set it from constant icon markup and kit fragment files, never from user text. Our own code never uses it (`tests/test_pages.py` checks that).
- **No network:** nothing in the vendored files requests another site. The fonts are self-hosted (D-017).
