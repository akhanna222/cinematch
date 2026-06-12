"""Social matching + discovery routes (PRD §5.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Connection, User
from app.schemas.models import (
    CompatibilityResult,
    DiscoverProfile,
    UserPublic,
)
from app.security import get_current_user
from app.services.compatibility_service import discover, score_pair

router = APIRouter(prefix="/social", tags=["social"])


@router.get("/discover", response_model=list[DiscoverProfile])
def discover_feed(
    limit: int = 25,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Compatibility-ranked discovery feed (PRD SM-02)."""
    rows = discover(db, current.user_id, limit=limit)
    return [
        {
            "user": UserPublic.model_validate(r["user"]),
            "score": r["score"],
            "shared_favourites": r["shared_favourites"],
        }
        for r in rows
    ]


@router.get("/compatibility/{other_id}", response_model=CompatibilityResult)
def compatibility(
    other_id: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Full compatibility breakdown between the caller and another user (SM-05)."""
    if not db.get(User, other_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return score_pair(db, current.user_id, other_id)


@router.post("/connect/{target_id}", status_code=status.HTTP_201_CREATED)
def express_interest(
    target_id: str,
    intent: str = "friends",
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Express interest; mutual interest unlocks a thread (SM-03, dual opt-in)."""
    if target_id == current.user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot connect to yourself")
    if not db.get(User, target_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # Did the target already express interest in us? -> mutual.
    reciprocal = db.scalar(
        select(Connection).where(
            Connection.initiator_id == target_id,
            Connection.target_id == current.user_id,
        )
    )
    conn = db.scalar(
        select(Connection).where(
            Connection.initiator_id == current.user_id,
            Connection.target_id == target_id,
        )
    )
    if conn is None:
        conn = Connection(
            initiator_id=current.user_id, target_id=target_id, intent=intent
        )
        db.add(conn)

    if reciprocal is not None:
        conn.status = "mutual"
        reciprocal.status = "mutual"
    db.commit()
    return {"status": conn.status, "mutual": conn.status == "mutual"}


@router.post("/block/{target_id}", status_code=status.HTTP_200_OK)
def block_user(
    target_id: str,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Block a user (SM-06, safety non-negotiable)."""
    conn = db.scalar(
        select(Connection).where(
            or_(
                (Connection.initiator_id == current.user_id)
                & (Connection.target_id == target_id),
                (Connection.initiator_id == target_id)
                & (Connection.target_id == current.user_id),
            )
        )
    )
    if conn is None:
        conn = Connection(
            initiator_id=current.user_id, target_id=target_id, status="blocked"
        )
        db.add(conn)
    else:
        conn.status = "blocked"
    db.commit()
    return {"status": "blocked"}
