# Database Design (PostgreSQL 17)

Locally: PostgreSQL as a **StatefulSet** on minikube (or the Compose service). On AWS: **RDS PostgreSQL** (already in Terraform).

Schema is plain SQL in `app/liveask/schema.sql`, applied by `python -m liveask.migrate` (run as an **initContainer**). The migrate command takes a Postgres **advisory lock** (`pg_advisory_lock(4242)`) so that two pods starting at the same time do not race. Every statement is idempotent (`CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

## Tables

```sql
CREATE TABLE IF NOT EXISTS room (
  id              BIGSERIAL PRIMARY KEY,
  code            CHAR(6) NOT NULL UNIQUE,         -- e.g. K7PX4M
  title           VARCHAR(120) NOT NULL,
  host_token_hash CHAR(64) NOT NULL,               -- sha256 hex; the token itself is never stored
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at      TIMESTAMPTZ NOT NULL DEFAULT now() + interval '24 hours',
  closed_at       TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS question (
  id          BIGSERIAL PRIMARY KEY,
  room_id     BIGINT NOT NULL REFERENCES room(id) ON DELETE CASCADE,
  text        VARCHAR(280) NOT NULL,
  author_name VARCHAR(40),
  device_id   UUID NOT NULL,
  status      VARCHAR(10) NOT NULL DEFAULT 'open' CHECK (status IN ('open','answered','hidden')),
  votes       INTEGER NOT NULL DEFAULT 0,          -- counter, updated in the same transaction as question_vote
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS question_room_idx ON question (room_id, votes DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS question_vote (
  question_id BIGINT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  device_id   UUID NOT NULL,
  PRIMARY KEY (question_id, device_id)             -- one vote per device
);

CREATE TABLE IF NOT EXISTS poll (
  id         BIGSERIAL PRIMARY KEY,
  room_id    BIGINT NOT NULL REFERENCES room(id) ON DELETE CASCADE,
  question   VARCHAR(200) NOT NULL,
  options    JSONB NOT NULL,                       -- ["Yes","No","Maybe"], 2..6 items
  status     VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','open','closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS poll_vote (
  poll_id      BIGINT NOT NULL REFERENCES poll(id) ON DELETE CASCADE,
  device_id    UUID NOT NULL,
  option_index SMALLINT NOT NULL,
  PRIMARY KEY (poll_id, device_id)                 -- one vote per device; changing vote = UPDATE
);
```

## Real-time fan-out with `LISTEN/NOTIFY`

Every write that changes what clients see ends with, **in the same transaction**:

```sql
SELECT pg_notify('liveask_events', '{"room":"K7PX4M","type":"question.updated","id":42}');
```

- Each pod keeps **one** dedicated connection that runs `LISTEN liveask_events`.
- When a notification arrives, the pod loads the changed object and sends it to **its own** WebSocket clients in that room.
- Postgres delivers notifications only after the transaction commits, so clients never see data that was rolled back.
- The payload limit is 8000 bytes, so events carry only type and IDs; the pod reads the object from the DB.

Event types: `question.created`, `question.updated` (votes or status), `poll.created`, `poll.updated` (status or results), `room.closed`.

## Cleanup

The `cleanup` CronJob runs `DELETE FROM room WHERE expires_at < now()` every night (cascades to all child rows) and logs how many rooms were removed.
