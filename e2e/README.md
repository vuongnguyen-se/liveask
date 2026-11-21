# Browser checks (development only)

Real-browser checks for the three views (host, audience, projector screen). They run against
the Docker Compose stack, so they exercise nginx and two app containers like the real thing.
They are not part of the Docker image and not run in CI.

## Run

```powershell
# from the repository root
docker compose up --build -d
cd e2e
npm install            # once; installs playwright-core only (no browser is downloaded)
npm run all            # or: npm test  /  npm run reconnect
```

Git Bash is the same. It uses the Chrome or Edge already on your machine; point to another one
with `BROWSER_PATH`. `BASE_URL` changes the address (default `http://localhost:8000`, or the
port you set with `LIVEASK_PORT`). `SHOTS_DIR=some\folder npm test` also saves screenshots of
the screen, phone and host views.

| Script | What it proves |
|---|---|
| `run.js` | Host and screen are on **different containers** yet update each other: question, upvote and unvote, hide, poll create/open/vote/change, close. Text such as `<img onerror=...>` shows as plain text. No JavaScript errors |
| `reconnect.js` | Stopping the container a screen uses makes it show "reconnecting", then reconnect by itself and show a question posted while it was away (uses `docker compose stop` and `start`) |

Every line prints `PASS` or `FAIL`; the exit code is non-zero if anything fails.

## The selector contract

The checks find things by id and class: `#status`, `#title`, `#code`, `#qr`, `#text`, `#name`,
`#ask`, `#questions .question`, `.vote`, `#polls .option`, `#poll-form`, `#poll-question`,
`#poll-options`, `#close-room`, `#closed`, and the buttons named "Hide", "Mark answered",
"Open for voting". **Keep these when restyling**, or change the checks in the same commit.

## Gotcha

nginx rotates containers per request, and a page load makes a fixed number of requests, so
every new page can land on the same container. `run.js` shifts the rotation with one extra
request until it reaches the other container.
