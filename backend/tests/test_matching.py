"""Tests for the Watch Night matching engine (PRD §5.2 / §14.2)."""

from app.core.matching import Swipe, run_match


def _swipes(mapping: dict[str, dict[str, str]]) -> list[Swipe]:
    """mapping: {participant: {content_id: signal}}."""
    out = []
    for pid, picks in mapping.items():
        for cid, sig in picks.items():
            out.append(Swipe(participant_id=pid, content_id=cid, signal=sig))
    return out


def test_full_consensus_ranks_first():
    swipes = _swipes(
        {
            "p1": {"dune": "strong_yes", "barbie": "pass"},
            "p2": {"dune": "interested", "barbie": "interested"},
        }
    )
    results = run_match(swipes, ["p1", "p2"])
    assert results[0].content_id == "dune"
    assert results[0].full_consensus is True
    # barbie is not full consensus (p1 passed).
    assert all(not r.full_consensus or r.content_id == "dune" for r in results)


def test_strong_yes_counts_double():
    # Both interested in A; one strong_yes + one interested on B.
    swipes = _swipes(
        {
            "p1": {"a": "interested", "b": "strong_yes"},
            "p2": {"a": "interested", "b": "interested"},
        }
    )
    results = run_match(swipes, ["p1", "p2"])
    # B aggregate = 2 + 1 = 3; A = 1 + 1 = 2. Both full consensus -> B first.
    assert results[0].content_id == "b"
    assert results[0].aggregate_score == 3


def test_partial_fallback_always_returns_result():
    # No title gets full consensus, but engine must still return something.
    swipes = _swipes(
        {
            "p1": {"a": "interested", "b": "pass"},
            "p2": {"a": "pass", "b": "interested"},
            "p3": {"a": "interested", "b": "pass"},
        }
    )
    results = run_match(swipes, ["p1", "p2", "p3"])
    assert len(results) > 0
    assert all(not r.full_consensus for r in results)
    # 'a' has 2/3 positive vs 'b' 1/3 -> a ranks first.
    assert results[0].content_id == "a"
    assert results[0].positive_count == 2


def test_dissenters_annotated():
    swipes = _swipes(
        {
            "p1": {"a": "interested"},
            "p2": {"a": "pass"},
        }
    )
    results = run_match(swipes, ["p1", "p2"])
    assert "p2" in results[0].dissenters


def test_titles_with_no_positive_signal_excluded():
    swipes = _swipes({"p1": {"a": "pass"}, "p2": {"a": "pass"}})
    assert run_match(swipes, ["p1", "p2"]) == []


def test_empty_participants_returns_empty():
    assert run_match([], []) == []


def test_top_n_limit():
    swipes = _swipes(
        {"p1": {f"m{i}": "interested" for i in range(10)}}
    )
    results = run_match(swipes, ["p1"], top_n=3)
    assert len(results) == 3
