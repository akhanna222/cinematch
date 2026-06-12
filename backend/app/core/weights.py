"""Config-driven model weights and tuning levers.

Per PRD §14.6, every weight is a config value so the product team can run
experiments without retraining. These defaults can be overridden at runtime
via environment variables (see app.config.Settings) or per-request overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

# --- Compatibility composite weights (PRD §7 / §14.3) -----------------------
# Must sum to 1.0.
DEFAULT_COMPATIBILITY_WEIGHTS: Dict[str, float] = {
    "genre_overlap": 0.30,  # genre cosine similarity
    "favourite_overlap": 0.35,  # favourite Jaccard (love + like sets)
    "rating_correlation": 0.25,  # rating Pearson r, rescaled to [0, 1]
    "watchlist_overlap": 0.10,  # watchlist Jaccard
}

# --- Explicit rating signal mapping (PRD §14.1) -----------------------------
RATING_SIGNAL_VALUES: Dict[str, float] = {
    "love": 1.0,
    "like": 0.6,
    "dislike": 0.0,
    "want": 0.3,  # "Want to Watch" interest boost
}

# Implicit / aspirational signals.
WATCHLIST_IMPLICIT_RATING = 0.4  # saves and shares treated as 0.4 positive

# --- Watch Night swipe signal mapping (PRD §14.2) ---------------------------
SWIPE_SIGNAL_VALUES: Dict[str, int] = {
    "pass": 0,  # swipe left
    "interested": 1,  # swipe right
    "strong_yes": 2,  # swipe up (counts double vs interested)
}

# --- Social matching gate (PRD §7 / §14.3) ----------------------------------
MIN_RATINGS_FOR_SOCIAL = 20
MIN_SHARED_TITLES_FOR_CORRELATION = 5

# --- Recommendation blend (PRD §14.4) ---------------------------------------
COLLAB_NEIGHBOUR_MIN_SCORE = 0.5  # only neighbours with compat >= 0.5
ALPHA_RATING_SCALE = 100.0  # alpha = min(rating_count / 100, ALPHA_CAP)
ALPHA_CAP = 0.7


@dataclass
class TuningLevers:
    """User / product-adjustable tuning levers (PRD §14.5).

    Each is a single float exposed to users or PMs without code changes.
    """

    # Lever 1 — recency bias. Higher favours recent taste shifts.
    #   0.1 -> ~7yr half-life, 0.4 -> ~1.7yr (default), 1.0 -> ~8mo.
    recency_lambda: float = 0.4

    # Lever 2 — diversity injection. Higher surfaces more novel titles.
    #   0.0 pure accuracy, 0.25 default, 0.6+ explorer mode.
    diversity_delta: float = 0.25

    # Lever 3 — social weight override. If set, replaces the automatic
    #   alpha = min(rating_count / 100, 0.7) schedule. Range [0.0, 0.7].
    alpha_override: float | None = None

    def clamp(self) -> "TuningLevers":
        """Clamp levers to their valid ranges."""
        self.recency_lambda = max(0.0, self.recency_lambda)
        self.diversity_delta = min(max(self.diversity_delta, 0.0), 1.0)
        if self.alpha_override is not None:
            self.alpha_override = min(max(self.alpha_override, 0.0), ALPHA_CAP)
        return self


@dataclass
class CompatibilityWeights:
    """Composite weights for the compatibility score. Defaults from PRD §14.3."""

    weights: Dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_COMPATIBILITY_WEIGHTS)
    )

    def validate(self) -> "CompatibilityWeights":
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Compatibility weights must sum to 1.0, got {total}")
        return self
