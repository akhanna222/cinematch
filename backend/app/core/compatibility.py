"""Social compatibility score (PRD §7 / §14.3).

A weighted composite of four independent signals, each normalised to [0, 1]:
genre cosine, favourite Jaccard, rating Pearson, watchlist Jaccard.
Weights are config-driven (PRD §14.6) so PMs can tune without retraining.
"""

from __future__ import annotations

import math
from typing import Dict, Set

from app.core.movie_dna import MovieDNASnapshot
from app.core.weights import (
    DEFAULT_COMPATIBILITY_WEIGHTS,
    MIN_RATINGS_FOR_SOCIAL,
    MIN_SHARED_TITLES_FOR_CORRELATION,
)


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def pearson(shared: Dict[str, tuple[float, float]]) -> float:
    """Pearson r on shared-catalogue ratings, rescaled [-1,1] -> [0,1].

    Requires a minimum of MIN_SHARED_TITLES_FOR_CORRELATION overlapping
    titles; below that the correlation is too noisy to trust.
    """
    if len(shared) < MIN_SHARED_TITLES_FOR_CORRELATION:
        return 0.0
    xs = [v[0] for v in shared.values()]
    ys = [v[1] for v in shared.values()]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denom = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    return (num / denom + 1) / 2 if denom else 0.0


def genre_cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(v**2 for v in a.values()))
    mag_b = math.sqrt(sum(v**2 for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def compute_compatibility(
    u: MovieDNASnapshot,
    v: MovieDNASnapshot,
    weights: Dict[str, float] | None = None,
) -> dict:
    """Compute the composite compatibility score and its component breakdown.

    Returns a dict with 'score' (rounded [0,1]) and 'components' so the
    breakdown UI (SM-05) can show genre overlap, shared favourites, rating
    correlation, and watchlist intersection transparently.
    """
    weights = weights or DEFAULT_COMPATIBILITY_WEIGHTS

    shared_ratings = {
        cid: (u.ratings[cid], v.ratings[cid])
        for cid in u.ratings
        if cid in v.ratings
    }
    components = {
        "genre_overlap": genre_cosine(u.genre_weights, v.genre_weights),
        "favourite_overlap": jaccard(u.positives, v.positives),
        "rating_correlation": pearson(shared_ratings),
        "watchlist_overlap": jaccard(u.watchlist, v.watchlist),
    }
    score = sum(weights[k] * components[k] for k in weights)
    return {"score": round(score, 4), "components": components}


def is_eligible_for_social(snapshot: MovieDNASnapshot) -> bool:
    """Cold-start gate (PRD §7): need >= 20 ratings to enter the social pool."""
    return snapshot.rating_count >= MIN_RATINGS_FOR_SOCIAL
