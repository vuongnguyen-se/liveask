"""Room codes and host tokens.

The host token is a secret that only the presenter has. We store just its SHA-256 hash,
so a database leak does not give anyone host access.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# No 0/O/1/I: they look alike on a projector.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def generate_code() -> str:
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def generate_host_token() -> str:
    return secrets.token_urlsafe(32)  # 32 random bytes -> 43 URL-safe characters


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, stored_hash: str) -> bool:
    """Constant-time comparison, so response time does not leak how much matched."""
    return hmac.compare_digest(hash_token(token), stored_hash.strip())
