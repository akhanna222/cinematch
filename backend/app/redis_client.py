"""Redis cache accessor (PRD §6.1).

Lazily connects. If Redis is unavailable (e.g. local dev with no container),
callers degrade gracefully to no-cache rather than failing.
"""

from __future__ import annotations

from functools import lru_cache

import redis

from app.config import get_settings


@lru_cache
def get_redis() -> redis.Redis | None:
    settings = get_settings()
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:  # noqa: BLE001 — cache is optional
        return None
