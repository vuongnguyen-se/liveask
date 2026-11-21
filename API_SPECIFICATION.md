# API Specification

One FastAPI service serves the API, the WebSocket endpoint and the static pages. JSON everywhere. Errors: `{"error": {"code": "string", "message": "string"}}`.

**Identity**
- Audience devices send `X-Device-Id: <uuid>`, a random UUID the browser creates once and keeps in `localStorage`.
- Host-only calls send `Authorization: Bearer <host_token>`. The server compares `sha256(token)` with `room.host_token_hash` using a constant-time compare.

## Health (for Kubernetes probes)

| Method | Path | Meaning |
|---|---|---|
| GET | `/healthz` | Liveness: process is up. Never touches the DB |
| GET | `/readyz` | Readiness: DB reachable **and** the LISTEN connection is alive; 503 otherwise, and 503 while shutting down |

## Pages (static HTML + JS)

| Path | View |
|---|---|
| `/` | Create a room / join by code |
| `/r/{code}` | Audience (phone) |
| `/host/{code}#t=<token>` | Presenter controls. The token is in the URL **fragment**, so it is never sent to the server or written to load balancer logs |
| `/screen/{code}` | Projector view: QR code, top questions, live poll |

## Rooms

`POST /api/rooms` with body `{"title": "Cloud 101 – week 5"}` → `201`
```json
{"code": "K7PX4M", "title": "Cloud 101 – week 5", "host_token": "…43 chars…",
 "audience_url": "/r/K7PX4M", "screen_url": "/screen/K7PX4M", "host_url": "/host/K7PX4M#t=…",
 "expires_at": "2026-11-23T10:00:00Z"}
```
The `host_token` is returned **only once**.

`GET /api/rooms/{code}` → room snapshot: `{"code","title","closed","questions":[…],"polls":[…],"my_votes":{"questions":[ids],"polls":{"<poll_id>":option}}}`. `my_votes` uses `X-Device-Id`. Hidden questions are left out unless the caller is the host.

`POST /api/rooms/{code}/close` (host) → `204`, and sends `room.closed`.

## Questions

| Method | Path | Who | Body / result |
|---|---|---|---|
| POST | `/api/rooms/{code}/questions` | audience | `{"text": "...", "author_name": "Lan"}` → `201` question. `429` if over 5/min per device |
| POST | `/api/questions/{id}/vote` | audience | toggles this device's vote → `{"id": 42, "votes": 7, "voted": true}` |
| PATCH | `/api/questions/{id}` | host | `{"status": "answered" \| "hidden" \| "open"}` |

Question object: `{"id": 42, "text": "...", "author_name": "Lan", "votes": 7, "status": "open", "created_at": "..."}`.

## Polls

| Method | Path | Who | Body / result |
|---|---|---|---|
| POST | `/api/rooms/{code}/polls` | host | `{"question": "Which AWS service next?", "options": ["EKS", "ECS", "Lambda"]}` → `201` (status `draft`) |
| PATCH | `/api/polls/{id}` | host | `{"status": "open" \| "closed"}` |
| POST | `/api/polls/{id}/vote` | audience | `{"option_index": 1}`; only while `open`; changing the vote is allowed |

Poll object: `{"id": 3, "question": "...", "options": ["EKS","ECS","Lambda"], "status": "open", "counts": [12, 5, 3], "total": 20}`.

## WebSocket

`GET /ws/rooms/{code}` (upgrade). Optional query `role=screen|host|audience`, used for logging only.

- **Server → client** messages: `{"type": "question.created", "data": {question}}`, `question.updated`, `poll.created`, `poll.updated`, `room.closed`, and `{"type": "hello", "data": {"pod": "<hostname>"}}` on connect. The UI shows "connected to pod …", which makes the multi-pod demo visible.
- **Client → server:** only `{"type": "ping"}` every 25 s; the server replies `pong`. All writes go through the REST endpoints above, which keeps WebSocket handling simple.
- On shutdown the server closes sockets with code **1012** (service restart). Clients reconnect with backoff (0.5 s, 1 s, 2 s … max 10 s) and call `GET /api/rooms/{code}` to resync.
