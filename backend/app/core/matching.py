"""Watch Night matching engine (PRD §5.2 / §14.2).

Server-side aggregation over per-participant swipe signals. No participant
sees others' choices during the swipe phase (anti-anchoring). The engine
MUST always return a result — partial-match fallback when there is no full
consensus (WN-08). Target runtime < 500ms.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from app.core.weights import SWIPE_SIGNAL_VALUES


@dataclass
class Swipe:
    participant_id: str
    content_id: str
    signal: str  # pass | interested | strong_yes

    @property
    def value(self) -> int:
        return SWIPE_SIGNAL_VALUES[self.signal]


@dataclass
class MatchResult:
    content_id: str
    aggregate_score: int  # sum of participant signal values
    full_consensus: bool  # every participant signalled >= 1 (interested+)
    positive_count: int  # participants who signalled >= 1
    total_participants: int
    dissenters: List[str] = field(default_factory=list)  # who passed / sat out
    fallback_score: float = 0.0  # coverage * avg_signal (partial matches)

    def as_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "aggregate_score": self.aggregate_score,
            "full_consensus": self.full_consensus,
            "positive_count": self.positive_count,
            "total_participants": self.total_participants,
            "dissenters": self.dissenters,
            "fallback_score": round(self.fallback_score, 4),
        }


def run_match(
    swipes: List[Swipe],
    participant_ids: List[str],
    deck: List[str] | None = None,
    top_n: int = 3,
) -> List[MatchResult]:
    """Aggregate swipes into ranked consensus picks.

    Ranking (PRD §14.2):
      * Full-consensus titles first (all participants signalled >= 1),
        ordered by aggregate signal (Strong Yes counts double).
      * If none, partial-match fallback ranked by
        fallback_score = (participants_positive / total) * avg_signal.

    Always returns up to ``top_n`` results; never an empty list when any
    title received at least one positive signal.
    """
    total = len(participant_ids)
    if total == 0:
        return []

    # Aggregate per title.
    agg: Dict[str, int] = defaultdict(int)
    positives: Dict[str, set] = defaultdict(set)
    seen_titles: set = set()

    for s in swipes:
        seen_titles.add(s.content_id)
        agg[s.content_id] += s.value
        if s.value >= 1:
            positives[s.content_id].add(s.participant_id)

    # Consider the full deck if provided so titles nobody swiped still appear
    # as (zero-signal) candidates for transparency; otherwise only seen ones.
    candidates = set(deck) if deck else seen_titles

    results: List[MatchResult] = []
    for cid in candidates:
        pos = positives.get(cid, set())
        pos_count = len(pos)
        avg_signal = agg[cid] / total if total else 0.0
        full = pos_count == total and total > 0
        dissenters = [p for p in participant_ids if p not in pos]
        results.append(
            MatchResult(
                content_id=cid,
                aggregate_score=agg[cid],
                full_consensus=full,
                positive_count=pos_count,
                total_participants=total,
                dissenters=dissenters,
                fallback_score=(pos_count / total) * avg_signal if total else 0.0,
            )
        )

    # Drop titles nobody was positive about — they are never a "match".
    results = [r for r in results if r.positive_count > 0]

    # Full consensus first, then by aggregate score; ties broken by coverage.
    results.sort(
        key=lambda r: (r.full_consensus, r.aggregate_score, r.fallback_score),
        reverse=True,
    )
    return results[:top_n]
