"""Limit how many rooms one network address can create per hour.

The count lives in this process's memory: no address is written to the database or to a log
(NFR-8). Each pod counts on its own, so the real ceiling is the limit times the number of
replicas, which is plenty to stop a script from filling the database.
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import Request

from liveask.config import get_settings

WINDOW_SECONDS = 3600
SWEEP_ABOVE = 10_000  # when this many addresses are tracked, drop the ones with no recent hit


class SlidingWindow:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}

    def clear(self) -> None:
        self._hits.clear()

    def retry_after(self, key: str, limit: int, window: float, now: float | None = None) -> int:
        """Record a hit and return 0, or return the seconds to wait when `key` is over `limit`."""
        now = time.monotonic() if now is None else now
        if len(self._hits) > SWEEP_ABOVE:
            self._sweep(window, now)
        hits = self._hits.setdefault(key, deque())
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, int(window - (now - hits[0])) + 1)  # a rejected try is not counted
        hits.append(now)
        return 0

    def _sweep(self, window: float, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= window]:
            del self._hits[key]


room_creations = SlidingWindow()


def client_ip(request: Request) -> str:
    """The caller's address. Behind a trusted proxy the proxy appends the real address to the
    right of X-Forwarded-For, so count `trusted_proxy_hops` entries from the right (anything
    further left was sent by the caller and can be forged). 0 hops: use the socket address."""
    hops = get_settings().trusted_proxy_hops
    if hops > 0:
        parts = [
            p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()
        ]
        if len(parts) >= hops:
            return parts[-hops]
    return request.client.host if request.client else "unknown"


def room_creation_retry_after(request: Request) -> int:
    """0 when this caller may create a room now, else how many seconds until they may."""
    limit = get_settings().rooms_per_hour_per_ip
    if limit <= 0:  # 0 turns the limit off
        return 0
    return room_creations.retry_after(client_ip(request), limit, WINDOW_SECONDS)
