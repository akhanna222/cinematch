"""Watch Night routes + WebSocket result push (PRD §5.2 / §8.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GuestParticipant, WatchSession
from app.realtime import session_hub
from app.schemas.models import (
    JoinRequest,
    SessionCreate,
    SessionPublic,
    SessionResult,
    SwipeCreate,
)
from app.security import oauth2_scheme  # optional auth for hosts
from app.services import session_service

router = APIRouter(prefix="/sessions", tags=["watch-night"])


def _load(db: Session, session_id: str) -> WatchSession:
    session = db.get(WatchSession, session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


@router.post("", response_model=SessionPublic, status_code=status.HTTP_201_CREATED)
def create(
    body: SessionCreate,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
) -> WatchSession:
    """Create a session. Host may be anonymous (guest hosting allowed)."""
    session = session_service.create_session(db, host_user_id=None, **body.model_dump())
    db.commit()
    db.refresh(session)
    return session


@router.post("/join/{code}", response_model=dict)
def join(code: str, body: JoinRequest, db: Session = Depends(get_db)) -> dict:
    """Join via 6-char code — no account required (WN-01)."""
    session, participant = session_service.join_session(
        db, code, body.display_name, body.user_id
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid join code")
    db.commit()
    return {"session_id": session.session_id, "participant_id": participant.participant_id}


@router.get("/{session_id}", response_model=SessionPublic)
def get_session(session_id: str, db: Session = Depends(get_db)) -> WatchSession:
    return _load(db, session_id)


@router.post("/{session_id}/start", response_model=SessionPublic)
def start(session_id: str, db: Session = Depends(get_db)) -> WatchSession:
    session = _load(db, session_id)
    session.status = "swiping"
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/swipe", status_code=status.HTTP_202_ACCEPTED)
def swipe(session_id: str, body: SwipeCreate, db: Session = Depends(get_db)) -> dict:
    session = _load(db, session_id)
    session_service.record_swipe(
        db, session, body.participant_id, body.content_id, body.signal
    )
    db.commit()
    return {"recorded": True}


@router.post("/{session_id}/complete/{participant_id}", response_model=dict)
async def complete_participant(
    session_id: str, participant_id: str, db: Session = Depends(get_db)
) -> dict:
    """Mark a participant done. When all are done, run the match and push it.

    Result is pushed to all connected clients via WebSocket (WN-06).
    """
    session = _load(db, session_id)
    participant = db.get(GuestParticipant, participant_id)
    if not participant or participant.session_id != session_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    participant.completed = True
    db.commit()

    progress = {
        "done": sum(1 for p in session.participants if p.completed),
        "total": len(session.participants),
    }
    await session_hub.broadcast(session_id, {"type": "progress", **progress})

    if session_service.all_completed(session):
        picks = session_service.compute_result(db, session)
        db.commit()
        await session_hub.broadcast(
            session_id, {"type": "result", "session_id": session_id, "picks": picks}
        )
        return {"complete": True, "picks": picks}
    return {"complete": False, **progress}


@router.get("/{session_id}/result", response_model=SessionResult)
def get_result(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = _load(db, session_id)
    if session.status != "complete":
        # Compute on demand if not all clients hit the WS path.
        picks = session_service.compute_result(db, session)
        db.commit()
    else:
        picks = session.result or []
    return {"session_id": session_id, "picks": picks}
