"""Social graph models: CompatibilityEdge and Connection (PRD §6.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CompatibilityEdge(Base):
    __tablename__ = "compatibility_edges"
    # Store the undirected pair once with user_a < user_b ordering.
    __table_args__ = (UniqueConstraint("user_a", "user_b", name="uq_compat_pair"),)

    edge_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_a: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    user_b: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    score: Mapped[float] = mapped_column(Float)  # 0.0 - 1.0
    genre_overlap: Mapped[float] = mapped_column(Float, default=0.0)
    favourite_overlap: Mapped[float] = mapped_column(Float, default=0.0)
    rating_correlation: Mapped[float] = mapped_column(Float, default=0.0)
    watchlist_overlap: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    version: Mapped[int] = mapped_column(Integer, default=1)  # increments on recalc


class Connection(Base):
    __tablename__ = "connections"
    __table_args__ = (
        UniqueConstraint("initiator_id", "target_id", name="uq_connection_pair"),
    )

    connection_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    initiator_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    target_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|mutual|blocked
    intent: Mapped[str] = mapped_column(String, default="friends")  # friends | dating
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
