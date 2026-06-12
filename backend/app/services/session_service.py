"""Watch Night session service (PRD §5.2 / §14.2)."""

from __future__ import annotations

import random
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.matching import Swipe, run_match
from app.models import GuestParticipant, SwipeRecord, WatchSession

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _gen_join_code(db: Session) -> str:
    """Generate a unique 6-character join code (WN-01)."""
    for _ in range(20):
        code = "".join(random.choices(_CODE_ALPHABET, k=6))
        if not db.scalar(select(WatchSession).where(WatchSession.join_code == code)):
            return code
    raise RuntimeError("Could not allocate a unique join code")


def create_session(db: Session, host_user_id: str | None, **config) -> WatchSession:
    session = WatchSession(
        join_code=_gen_join_code(db),
        host_user_id=host_user_id,
        services=config.get("services", []),
        rating_ceiling=config.get("rating_ceiling"),
        mood_seed=config.get("mood_seed"),
        max_runtime=config.get("max_runtime"),
        deck=config.get("deck", []),
        status="lobby",
    )
    db.add(session)
    db.flush()
    return session


def join_session(db: Session, code: str, display_name: str, user_id: str | None) -> tuple:
    session = db.scalar(select(WatchSession).where(WatchSession.join_code == code.upper()))
    if session is None:
        return None, None
    participant = GuestParticipant(
        session_id=session.session_id, user_id=user_id, display_name=display_name
    )
    db.add(participant)
    db.flush()
    return session, participant


def record_swipe(db: Session, session: WatchSession, participant_id: str,
                 content_id: str, signal: str) -> None:
    db.add(
        SwipeRecord(
            session_id=session.session_id,
            participant_id=participant_id,
            content_id=content_id,
            signal=signal,
        )
    )
    db.flush()


def all_completed(session: WatchSession) -> bool:
    return bool(session.participants) and all(p.completed for p in session.participants)


def compute_result(db: Session, session: WatchSession) -> list[dict]:
    """Run the match engine and cache the result on the session.

    Always returns a non-empty result when any title was swiped positively
    (partial-match fallback, WN-08).
    """
    swipes = [
        Swipe(participant_id=s.participant_id, content_id=s.content_id, signal=s.signal)
        for s in db.scalars(
            select(SwipeRecord).where(SwipeRecord.session_id == session.session_id)
        ).all()
    ]
    participant_ids = [p.participant_id for p in session.participants]
    results = run_match(swipes, participant_ids, deck=session.deck or None)
    payload = [r.as_dict() for r in results]
    session.result = payload
    session.status = "complete"
    db.flush()
    return payload
