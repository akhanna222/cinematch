"""SQLAlchemy ORM models — the Postgres schema (PRD §6.2).

Importing this package registers every model on the shared metadata.
"""

from app.models.session import GuestParticipant, SwipeRecord, WatchSession  # noqa: F401
from app.models.social import CompatibilityEdge, Connection  # noqa: F401
from app.models.user import MovieDNA, Rating, StreamingSub, User  # noqa: F401

__all__ = [
    "User",
    "MovieDNA",
    "Rating",
    "StreamingSub",
    "CompatibilityEdge",
    "Connection",
    "WatchSession",
    "GuestParticipant",
    "SwipeRecord",
]
