"""Tests for the compatibility algorithm (PRD §7 / §14.3)."""

import math

from app.core.compatibility import (
    compute_compatibility,
    genre_cosine,
    is_eligible_for_social,
    jaccard,
    pearson,
)
from app.core.movie_dna import MovieDNASnapshot
from app.core.weights import DEFAULT_COMPATIBILITY_WEIGHTS


def test_weights_sum_to_one():
    assert abs(sum(DEFAULT_COMPATIBILITY_WEIGHTS.values()) - 1.0) < 1e-9


def test_jaccard_basic():
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a"}, {"a"}) == 1.0


def test_genre_cosine_identical_is_one():
    a = {"thriller": 0.8, "comedy": 0.4}
    assert abs(genre_cosine(a, a) - 1.0) < 1e-9


def test_genre_cosine_orthogonal_is_zero():
    assert genre_cosine({"thriller": 1.0}, {"comedy": 1.0}) == 0.0


def test_pearson_requires_minimum_overlap():
    # Fewer than 5 shared titles -> 0.0 (too noisy).
    assert pearson({"a": (1.0, 1.0), "b": (0.0, 0.0)}) == 0.0


def test_pearson_perfect_correlation_rescaled_to_one():
    shared = {str(i): (float(i), float(i)) for i in range(6)}
    assert abs(pearson(shared) - 1.0) < 1e-9


def test_pearson_perfect_anticorrelation_rescaled_to_zero():
    shared = {str(i): (float(i), float(5 - i)) for i in range(6)}
    assert abs(pearson(shared) - 0.0) < 1e-9


def test_compute_compatibility_identical_users_high_score():
    snap = MovieDNASnapshot(
        genre_weights={"thriller": 0.8, "comedy": 0.4},
        positives={"m1", "m2", "m3"},
        ratings={"m1": 1.0, "m2": 0.6, "m3": 1.0, "m4": 0.0, "m5": 1.0, "m6": 0.6},
        watchlist={"w1", "w2"},
        rating_count=25,
    )
    result = compute_compatibility(snap, snap)
    # Identical profiles: genre=1, fav=1, pearson=1, watchlist=1 -> ~1.0.
    assert result["score"] > 0.99
    assert math.isclose(result["components"]["favourite_overlap"], 1.0)


def test_compute_compatibility_disjoint_users_low_score():
    a = MovieDNASnapshot(
        genre_weights={"thriller": 1.0},
        positives={"m1", "m2"},
        ratings={"m1": 1.0, "m2": 1.0},
        watchlist={"w1"},
        rating_count=20,
    )
    b = MovieDNASnapshot(
        genre_weights={"comedy": 1.0},
        positives={"m9", "m8"},
        ratings={"m9": 1.0, "m8": 1.0},
        watchlist={"w9"},
        rating_count=20,
    )
    result = compute_compatibility(a, b)
    assert result["score"] == 0.0


def test_social_eligibility_gate():
    assert not is_eligible_for_social(MovieDNASnapshot(rating_count=19))
    assert is_eligible_for_social(MovieDNASnapshot(rating_count=20))


def test_configurable_weights_change_score():
    a = MovieDNASnapshot(genre_weights={"thriller": 1.0}, positives=set(), ratings={})
    b = MovieDNASnapshot(genre_weights={"thriller": 1.0}, positives=set(), ratings={})
    # Put all weight on genre overlap -> score should equal genre cosine (1.0).
    custom = {
        "genre_overlap": 1.0,
        "favourite_overlap": 0.0,
        "rating_correlation": 0.0,
        "watchlist_overlap": 0.0,
    }
    assert compute_compatibility(a, b, custom)["score"] == 1.0
