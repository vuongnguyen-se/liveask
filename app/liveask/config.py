"""Settings read from environment variables (set by the Kubernetes ConfigMap / Secret)."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    app_version: str
    pod_name: str
    log_level: str
    max_connections_per_room: int
    questions_per_minute: int
    rooms_per_hour_per_ip: int
    trusted_proxy_hops: int


def get_settings() -> Settings:
    """Read settings fresh each call, so tests can change the environment."""
    return Settings(
        database_url=os.getenv("DATABASE_URL") or None,
        app_version=os.getenv("APP_VERSION", "dev"),
        pod_name=os.getenv("POD_NAME") or socket.gethostname(),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        max_connections_per_room=int(os.getenv("MAX_CONNECTIONS_PER_ROOM", "300")),
        questions_per_minute=int(os.getenv("QUESTIONS_PER_MINUTE", "5")),
        rooms_per_hour_per_ip=int(os.getenv("ROOMS_PER_HOUR_PER_IP", "20")),
        trusted_proxy_hops=int(os.getenv("TRUSTED_PROXY_HOPS", "1")),
    )
