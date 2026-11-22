-- LiveAsk schema. Every statement is idempotent: it is safe to run on every pod start.

CREATE TABLE IF NOT EXISTS room (
  id              BIGSERIAL PRIMARY KEY,
  code            CHAR(6) NOT NULL UNIQUE,
  title           VARCHAR(120) NOT NULL,
  host_token_hash CHAR(64) NOT NULL,
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
  votes       INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS question_room_idx ON question (room_id, votes DESC, created_at DESC);
-- Used by the per-device rate limit.
CREATE INDEX IF NOT EXISTS question_device_idx ON question (device_id, created_at DESC);

CREATE TABLE IF NOT EXISTS question_vote (
  question_id BIGINT NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  device_id   UUID NOT NULL,
  PRIMARY KEY (question_id, device_id)
);

CREATE TABLE IF NOT EXISTS poll (
  id         BIGSERIAL PRIMARY KEY,
  room_id    BIGINT NOT NULL REFERENCES room(id) ON DELETE CASCADE,
  question   VARCHAR(200) NOT NULL,
  options    JSONB NOT NULL,
  status     VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','open','closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS poll_vote (
  poll_id      BIGINT NOT NULL REFERENCES poll(id) ON DELETE CASCADE,
  device_id    UUID NOT NULL,
  option_index SMALLINT NOT NULL,
  PRIMARY KEY (poll_id, device_id)
);
