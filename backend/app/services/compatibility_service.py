"""Compatibility + social discovery service (PRD §5.3 / §7)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.compatibility import compute_compatibility, is_eligible_for_social
from app.models import CompatibilityEdge, User
from app.services.profile_service import build_user_snapshot

settings = get_settings()


def score_pair(db: Session, user_a: str, user_b: str) -> dict:
    """Compute the compatibility result for two users (not persisted)."""
    snap_a = build_user_snapshot(db, user_a)
    snap_b = build_user_snapshot(db, user_b)
    result = compute_compatibility(snap_a, snap_b, settings.compatibility_weights)
    eligible = is_eligible_for_social(snap_a) and is_eligible_for_social(snap_b)
    shared = sorted(snap_a.positives & snap_b.positives)
    return {
        "user_a": user_a,
        "user_b": user_b,
        "score": result["score"],
        "components": result["components"],
        "eligible": eligible,
        "shared_favourites": shared,
    }


def upsert_edge(db: Session, user_a: str, user_b: str) -> CompatibilityEdge:
    """Compute and persist a CompatibilityEdge, bumping version on recalc.

    The pair is stored once with a stable ordering (user_a < user_b) so the
    undirected edge is not duplicated.
    """
    lo, hi = sorted((user_a, user_b))
    res = score_pair(db, lo, hi)
    edge = db.scalar(
        select(CompatibilityEdge).where(
            CompatibilityEdge.user_a == lo, CompatibilityEdge.user_b == hi
        )
    )
    if edge is None:
        edge = CompatibilityEdge(user_a=lo, user_b=hi, score=res["score"], version=1)
        db.add(edge)
    else:
        edge.score = res["score"]
        edge.version += 1
    c = res["components"]
    edge.genre_overlap = c["genre_overlap"]
    edge.favourite_overlap = c["favourite_overlap"]
    edge.rating_correlation = c["rating_correlation"]
    edge.watchlist_overlap = c["watchlist_overlap"]
    db.flush()
    return edge


def discover(db: Session, user_id: str, limit: int = 25) -> list[dict]:
    """Rank visible, eligible users by compatibility (PRD SM-02).

    v1 scores against all eligible candidates on demand. A later increment
    moves this to the precomputed CompatibilityEdge table with incremental
    refresh (PRD AI-04 / OQ-06).
    """
    me = build_user_snapshot(db, user_id)
    if not is_eligible_for_social(me):
        return []  # below the 20-rating gate (PRD §7)

    candidates = db.scalars(
        select(User).where(
            User.user_id != user_id,
            User.visible_to_matching == True,  # noqa: E712
            User.social_intent != "off",
        )
    ).all()

    ranked: list[dict] = []
    for cand in candidates:
        res = score_pair(db, user_id, cand.user_id)
        if not res["eligible"]:
            continue
        ranked.append(
            {
                "user": cand,
                "score": res["score"],
                "shared_favourites": res["shared_favourites"][:5],
            }
        )
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:limit]
