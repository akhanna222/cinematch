"""Tests for Movie DNA computation (PRD §14.1)."""

from datetime import datetime, timedelta, timezone

from app.core.movie_dna import (
    RatingEvent,
    build_snapshot,
    compute_genre_weights,
    recency_weight,
)


def _now():
    return datetime(2026, 6, 12, tzinfo=timezone.utc)


def test_genre_weight_formula():
    # thriller: love(1.0) + like(0.6) over 2 titles -> 0.8
    ratings = [
        RatingEvent("m1", "love", _now(), genres=("thriller",)),
        RatingEvent("m2", "like", _now(), genres=("thriller",)),
    ]
    weights = compute_genre_weights(ratings)
    assert abs(weights["thriller"] - 0.8) < 1e-9


def test_dislike_pulls_genre_weight_down():
    ratings = [
        RatingEvent("m1", "love", _now(), genres=("comedy",)),  # 1.0
        RatingEvent("m2", "dislike", _now(), genres=("comedy",)),  # 0.0
    ]
    weights = compute_genre_weights(ratings)
    assert abs(weights["comedy"] - 0.5) < 1e-9


def test_want_excluded_from_genre_weights():
    ratings = [RatingEvent("m1", "want", _now(), genres=("horror",))]
    assert compute_genre_weights(ratings) == {}


def test_recency_weight_decays():
    now = _now()
    recent = recency_weight(now, lambda_=0.4, now=now)
    old = recency_weight(now - timedelta(days=365), lambda_=0.4, now=now)
    assert recent == 1.0
    assert old < recent


def test_build_snapshot_positives_and_counts():
    ratings = [
        RatingEvent("m1", "love", _now(), genres=("thriller",)),
        RatingEvent("m2", "like", _now(), genres=("thriller",)),
        RatingEvent("m3", "dislike", _now(), genres=("comedy",)),
        RatingEvent("m4", "want", _now(), genres=("horror",)),
    ]
    snap = build_snapshot(ratings, watchlist=["w1"])
    assert snap.positives == {"m1", "m2"}
    # explicit ratings exclude 'want'
    assert snap.rating_count == 3
    assert "w1" in snap.watchlist
    # watchlist title gets soft implicit rating
    assert snap.ratings["w1"] == 0.4
