"""In-process WebSocket hub for Watch Night sessions (PRD WN-06).

Pushes swipe progress and final match results to all participants. For a
single-process dev/MVP deployment this in-memory hub is sufficient; scale-out
swaps it for a Redis pub/sub fan-out without changing the route code.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class SessionHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms[session_id].add(ws)

    async def disconnect(self, session_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[session_id].discard(ws)
            if not self._rooms[session_id]:
                self._rooms.pop(session_id, None)

    async def broadcast(self, session_id: str, message: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(session_id, ()))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 — client gone; reap it
                dead.append(ws)
        for ws in dead:
            await self.disconnect(session_id, ws)


session_hub = SessionHub()
