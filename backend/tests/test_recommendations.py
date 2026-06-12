"""Tests for the recommendation engine (PRD §5.4 / §14.4)."""

from app.core.recommendations import (
    Neighbour,
    collab_alpha,
    collaborative_scores,
    hybrid_recommend,
    paired_recommend,
)


def test_alpha_schedule():
    assert collab_alpha(0) == 0.0
    assert collab_alpha(50) == 0.5
    assert collab_alpha(100) == 0.7
    assert collab_alpha(1000) == 0.7  # capped


def test_alpha_override_respected_and_clamped():
    assert collab_alpha(0, alpha_override=0.5) == 0.5
    assert collab_alpha(1000, alpha_override=0.9) == 0.7  # clamped to cap


def test_collaborative_excludes_low_similarity_neighbours():
    neighbours = [
        Neighbour("v1", similarity=0.9, ratings={"x": 1.0}),
        Neighbour("v2", similarity=0.2, ratings={"y": 1.0}),  # below 0.5 cutoff
    ]
    scores = collaborative_scores(seen=set(), neighbours=neighbours)
    assert "x" in scores
    assert "y" not in scores


def test_collaborative_excludes_seen_titles():
    neighbours = [Neighbour("v1", 0.9, {"seen_movie": 1.0, "new_movie": 1.0})]
    scores = collaborative_scores(seen={"seen_movie"}, neighbours=neighbours)
    assert "seen_movie" not in scores
    assert "new_movie" in scores


def test_paired_uses_min_not_average():
    # PRD example: Alex 3.5, Sam 1.2 -> pair score 1.2.
    picks = paired_recommend({"dune": 3.5}, {"dune": 1.2})
    assert picks == [("dune", 1.2)]


def test_paired_only_shared_candidates():
    picks = paired_recommend({"a": 1.0, "b": 0.5}, {"a": 0.8})
    assert [c for c, _ in picks] == ["a"]


def test_hybrid_cold_start_is_content_based():
    # 0 ratings -> alpha 0 -> pure content. A title similar to taste wins.
    catalogue = {
        "match": {"thriller": 1.0},
        "other": {"comedy": 1.0},
    }
    recs = hybrid_recommend(
        rating_count=0,
        seen=set(),
        neighbours=[],
        taste_vector={"thriller": 1.0},
        catalogue=catalogue,
        diversity_delta=0.0,  # isolate relevance
    )
    assert recs[0][0] == "match"


def test_hybrid_returns_unseen_only():
    catalogue = {"a": {"g": 1.0}, "b": {"g": 1.0}}
    recs = hybrid_recommend(
        rating_count=10,
        seen={"a"},
        neighbours=[],
        taste_vector={"g": 1.0},
        catalogue=catalogue,
    )
    assert all(cid != "a" for cid, _ in recs)
