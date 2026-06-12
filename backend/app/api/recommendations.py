"""Recommendation routes (PRD §5.4). Thin wrapper over the core engine.

The full personalised feed needs a TMDB-backed catalogue feature store, which
arrives in a later increment. This route exposes the paired-recommendation
endpoint (AI-02) which only needs in-graph data, plus the tuning levers so the
client can preview lever effects.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.recommendations import collab_alpha, paired_recommend
from app.database import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class PairedRequest(BaseModel):
    # content_id -> predicted score, for each user. Supplied by the client/
    # collaborative pass until the server-side catalogue store lands.
    pred_self: dict[str, float]
    pred_other: dict[str, float]
    top_n: int = 20


class AlphaResponse(BaseModel):
    rating_count: int
    alpha: float


@router.get("/alpha", response_model=AlphaResponse)
def my_alpha(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> AlphaResponse:
    """Current collaborative blend weight for the caller (PRD §14.4)."""
    count = current.dna.rating_count if current.dna else 0
    return AlphaResponse(rating_count=count, alpha=collab_alpha(count))


@router.post("/paired")
def paired(body: PairedRequest, _: User = Depends(get_current_user)) -> dict:
    """Titles both connected users will likely enjoy but neither has seen (AI-02)."""
    picks = paired_recommend(body.pred_self, body.pred_other, top_n=body.top_n)
    return {"picks": [{"content_id": c, "pair_score": round(s, 4)} for c, s in picks]}
