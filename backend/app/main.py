"""CineMatch API entrypoint (PRD §6.1).

Wires the API Gateway: auth, profile, social, watch-night, and recommendation
services behind a single FastAPI app, plus the Watch Night WebSocket.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, profiles, recommendations, sessions, social
from app.config import get_settings
from app.database import init_db
from app.realtime import session_hub

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience: ensure tables exist. Production relies on Alembic.
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="CineMatch — social discovery through shared taste. v1 MVP.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten per-environment before GA
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(social.router)
app.include_router(sessions.router)
app.include_router(recommendations.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "version": "0.1.0"}


@app.websocket("/ws/sessions/{session_id}")
async def watch_night_ws(websocket: WebSocket, session_id: str) -> None:
    """Real-time channel for a Watch Night session (progress + result push)."""
    await session_hub.connect(session_id, websocket)
    try:
        while True:
            # Clients aren't required to send anything; keep the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await session_hub.disconnect(session_id, websocket)
