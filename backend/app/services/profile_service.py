"""Profile + Movie DNA service: turns rating rows into a DNA snapshot.

Bridges the SQLAlchemy layer to the pure ``app.core`` algorithms.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.movie_dna import MovieDNASnapshot, RatingEvent, build_snapshot
from app.models import MovieDNA, Rating, User


def _rating_events(db: Session, user_id: str) -> list[RatingEvent]:
    rows = db.scalars(select(Rating).where(Rating.user_id == user_id)).all()
    return [
        RatingEvent(
            content_id=r.content_id,
            signal=r.signal,
            rated_at=r.rated_at,
            genres=tuple(r.genres or []),
        )
        for r in rows
    ]


def build_user_snapshot(db: Session, user_id: str, recency_lambda: float = 0.0) -> MovieDNASnapshot:
    """Compute a fresh DNA snapshot for a user from their ratings + watchlist."""
    events = _rating_events(db, user_id)
    watchlist = [r.content_id for r in db.scalars(
        select(Rating).where(Rating.user_id == user_id, Rating.signal == "want")
    ).all()]
    return build_snapshot(events, watchlist=watchlist, recency_lambda=recency_lambda)


def recompute_dna(db: Session, user: User) -> MovieDNA:
    """Recompute and persist the user's MovieDNA row (PRD MD-03)."""
    snapshot = build_user_snapshot(db, user.user_id)
    dna = db.get(MovieDNA, user.user_id)
    if dna is None:
        dna = MovieDNA(user_id=user.user_id)
        db.add(dna)
    dna.genre_weights = snapshot.genre_weights
    dna.rating_count = snapshot.rating_count
    db.flush()
    return dna
