"""Movie DNA profile computation (PRD §14.1).

Derives the numeric taste signals — genre weights, positive/watchlist sets,
and normalised ratings — from a user's raw rating events. Everything
downstream (compatibility, recommendations) depends on this layer.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, Set

from app.core.weights import (
    RATING_SIGNAL_VALUES,
    WATCHLIST_IMPLICIT_RATING,
)


@dataclass
class RatingEvent:
    """A single explicit/implicit rating used for DNA computation."""

    content_id: str
    signal: str  # love | like | dislike | want
    rated_at: datetime
    # Optional content metadata used for genre weighting.
    genres: tuple[str, ...] = ()

    @property
    def score(self) -> float:
        return RATING_SIGNAL_VALUES[self.signal]


@dataclass
class MovieDNASnapshot:
    """The computed taste vector for a user (PRD §7).

    Mirrors the dataclass in the PRD compatibility algorithm so the
    compatibility module can consume it directly.
    """

    genre_weights: Dict[str, float] = field(default_factory=dict)
    positives: Set[str] = field(default_factory=set)  # love + like content_ids
    ratings: Dict[str, float] = field(default_factory=dict)  # content_id -> [0,1]
    watchlist: Set[str] = field(default_factory=set)
    rating_count: int = 0


def recency_weight(rated_at: datetime, lambda_: float, now: datetime | None = None) -> float:
    """Exponential decay weight (PRD §14.5, Lever 1).

    decay(rating) = exp(-lambda * days_since_rating)
    """
    now = now or datetime.now(timezone.utc)
    if rated_at.tzinfo is None:
        rated_at = rated_at.replace(tzinfo=timezone.utc)
    days = max((now - rated_at).total_seconds() / 86400.0, 0.0)
    return math.exp(-lambda_ * days)


def compute_genre_weights(
    ratings: Iterable[RatingEvent],
    recency_lambda: float = 0.0,
    now: datetime | None = None,
) -> Dict[str, float]:
    """Weighted mean of the rating signal per genre (PRD §14.1).

        w[genre] = SUM(signal * freq) / SUM(freq)

    When recency_lambda > 0 each rating is additionally weighted by its
    exponential recency decay (Lever 1), so freq becomes the summed decay
    weight rather than a raw count.
    """
    numer: Dict[str, float] = defaultdict(float)
    denom: Dict[str, float] = defaultdict(float)

    for r in ratings:
        # "want" is an interest boost, not a quality signal — exclude from
        # genre weighting which measures how much a user *likes* a genre.
        if r.signal == "want":
            continue
        decay = recency_weight(r.rated_at, recency_lambda, now) if recency_lambda > 0 else 1.0
        for g in r.genres:
            numer[g] += r.score * decay
            denom[g] += decay

    return {g: numer[g] / denom[g] for g in numer if denom[g] > 0}


def build_snapshot(
    ratings: Iterable[RatingEvent],
    watchlist: Iterable[str] | None = None,
    recency_lambda: float = 0.0,
    now: datetime | None = None,
) -> MovieDNASnapshot:
    """Build a full DNA snapshot from raw rating events."""
    ratings = list(ratings)
    positives: Set[str] = set()
    normalised: Dict[str, float] = {}
    explicit_count = 0

    for r in ratings:
        if r.signal in ("love", "like"):
            positives.add(r.content_id)
        if r.signal != "want":
            # normalised quality score in [0, 1] for Pearson / collaborative use
            normalised[r.content_id] = r.score
            explicit_count += 1

    wl = set(watchlist or [])
    # Saves/shares act as a soft positive rating if not explicitly rated.
    for cid in wl:
        normalised.setdefault(cid, WATCHLIST_IMPLICIT_RATING)

    return MovieDNASnapshot(
        genre_weights=compute_genre_weights(ratings, recency_lambda, now),
        positives=positives,
        ratings=normalised,
        watchlist=wl,
        rating_count=explicit_count,
    )
