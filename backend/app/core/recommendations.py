"""Hybrid recommendation engine (PRD §5.4 / §14.4).

Blends collaborative filtering (taste-neighbour driven) with content-based
filtering (feature-similarity driven). The collaborative weight ``alpha``
rises automatically with rating count so content-based dominates at cold
start. Diversity injection (Lever 2) re-ranks for novelty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from app.core.weights import (
    ALPHA_CAP,
    ALPHA_RATING_SCALE,
    COLLAB_NEIGHBOUR_MIN_SCORE,
)


# --- alpha schedule ---------------------------------------------------------
def collab_alpha(rating_count: int, alpha_override: float | None = None) -> float:
    """alpha = min(rating_count / 100, 0.7), or a user override (PRD §14.4/14.5)."""
    if alpha_override is not None:
        return min(max(alpha_override, 0.0), ALPHA_CAP)
    return min(rating_count / ALPHA_RATING_SCALE, ALPHA_CAP)


# --- collaborative filtering ------------------------------------------------
@dataclass
class Neighbour:
    user_id: str
    similarity: float  # compatibility score in [0, 1]
    ratings: Dict[str, float]  # content_id -> normalised rating [0, 1]


def collaborative_scores(
    seen: Set[str],
    neighbours: Iterable[Neighbour],
    min_sim: float = COLLAB_NEIGHBOUR_MIN_SCORE,
) -> Dict[str, float]:
    """Weighted neighbour ratings (PRD §14.4).

        pred(u, i) = SUM(sim(u,v) * r(v,i)) / SUM(|sim(u,v)|)

    Only neighbours with similarity >= ``min_sim`` contribute. Titles the
    user has already seen are excluded.
    """
    numer: Dict[str, float] = {}
    denom: Dict[str, float] = {}
    for nb in neighbours:
        if nb.similarity < min_sim:
            continue
        for cid, r in nb.ratings.items():
            if cid in seen:
                continue
            numer[cid] = numer.get(cid, 0.0) + nb.similarity * r
            denom[cid] = denom.get(cid, 0.0) + abs(nb.similarity)
    return {cid: numer[cid] / denom[cid] for cid in numer if denom[cid] > 0}


# --- content-based filtering ------------------------------------------------
def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    mag_a = math.sqrt(sum(v**2 for v in a.values()))
    mag_b = math.sqrt(sum(v**2 for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def content_scores(
    taste_vector: Dict[str, float],
    catalogue: Dict[str, Dict[str, float]],
    seen: Set[str],
) -> Dict[str, float]:
    """Cosine similarity of each unseen title's feature vector to the user's
    aggregate taste vector (PRD §14.4). Features: genre tags, director, cast,
    country, language, decade bucket, runtime bucket — all encoded as a sparse
    weighted dict by the caller.
    """
    return {
        cid: cosine(taste_vector, feats)
        for cid, feats in catalogue.items()
        if cid not in seen
    }


# --- hybrid blend -----------------------------------------------------------
def _max_sim_to_seen(
    cid: str,
    catalogue: Dict[str, Dict[str, float]],
    seen: Set[str],
) -> float:
    feats = catalogue.get(cid)
    if not feats or not seen:
        return 0.0
    return max((cosine(feats, catalogue[s]) for s in seen if s in catalogue), default=0.0)


def hybrid_recommend(
    rating_count: int,
    seen: Set[str],
    neighbours: Iterable[Neighbour],
    taste_vector: Dict[str, float],
    catalogue: Dict[str, Dict[str, float]],
    *,
    alpha_override: float | None = None,
    diversity_delta: float = 0.25,
    top_n: int = 20,
) -> List[Tuple[str, float]]:
    """Blend collaborative + content signals, then re-rank for novelty.

        final = alpha * collab + (1 - alpha) * content        (relevance)
        rank  = (1 - delta) * relevance + delta * novelty      (Lever 2)
        novelty = 1 - max_cosine_sim(title, seen_titles)

    Returns the top-N (content_id, rank_score) pairs, descending.
    """
    alpha = collab_alpha(rating_count, alpha_override)
    collab = collaborative_scores(seen, neighbours)
    content = content_scores(taste_vector, catalogue, seen)

    candidates = (set(collab) | set(content)) - seen
    ranked: List[Tuple[str, float]] = []
    for cid in candidates:
        relevance = alpha * collab.get(cid, 0.0) + (1 - alpha) * content.get(cid, 0.0)
        novelty = 1.0 - _max_sim_to_seen(cid, catalogue, seen)
        rank = (1 - diversity_delta) * relevance + diversity_delta * novelty
        ranked.append((cid, rank))

    ranked.sort(key=lambda t: t[1], reverse=True)
    return ranked[:top_n]


# --- paired recommendations (Watch Night, PRD AI-02 / §14.4) ----------------
def paired_recommend(
    pred_u: Dict[str, float],
    pred_v: Dict[str, float],
    top_n: int = 20,
) -> List[Tuple[str, float]]:
    """Titles both connected users are likely to enjoy but neither has seen.

        pair_score(i) = min(pred(u, i), pred(v, i))

    min() prevents one user's enthusiasm from overriding the other's
    indifference (averaging would over-represent the keener user).
    """
    shared = set(pred_u) & set(pred_v)
    scored = [(cid, min(pred_u[cid], pred_v[cid])) for cid in shared]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_n]
