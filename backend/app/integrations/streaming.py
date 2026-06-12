"""TMDB / JustWatch integration layer (PRD §6.1, §13).

v1 scaffold: provides the deep-link builder and a cached-availability
interface. Live TMDB metadata and JustWatch availability calls are wired in a
later increment; until then ``availability`` returns an empty result and the
deep-link builder is fully functional for the v1 service set.

Streaming availability is cached with a 24h TTL (PRD risk table) because stale
availability is a top product risk for unwatchable match results.
"""

from __future__ import annotations

import json

from app.config import get_settings
from app.redis_client import get_redis

settings = get_settings()

# Deep-link templates for the v1 streaming service set (PRD §13).
DEEP_LINK_TEMPLATES: dict[str, str] = {
    "netflix": "netflix://title/{id}",
    "prime": "primevideo://detail/{id}",
    "appletv": "videos://tvshow?contentId={id}",
    "disney": "disneyplus://content/{id}",
    "max": "max://content/{id}",
}


def build_deep_link(service: str, content_id: str) -> str | None:
    """Return the app deep-link for a service + content id, or None if unknown."""
    template = DEEP_LINK_TEMPLATES.get(service)
    return template.format(id=content_id) if template else None


def availability(content_id: str) -> dict:
    """Return cached streaming availability for a title.

    Shape: {"services": ["netflix", ...], "deep_links": {service: url}}.
    Falls back to an empty result when JustWatch is disabled or uncached.
    """
    cache = get_redis()
    key = f"avail:{content_id}"
    if cache:
        cached = cache.get(key)
        if cached:
            return json.loads(cached)

    # Live JustWatch lookup goes here once enabled.
    result: dict = {"content_id": content_id, "services": [], "deep_links": {}}

    if cache:
        cache.setex(key, settings.streaming_cache_ttl_seconds, json.dumps(result))
    return result
