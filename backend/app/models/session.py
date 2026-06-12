"""Watch Night session models (PRD §5.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class WatchSession(Base):
    __tablename__ = "watch_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    join_code: Mapped[str] = mapped_column(String, unique=True, index=True)  # 6-char
    host_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    # Host config (WN-02).
    services: Mapped[list] = mapped_column(JSON, default=list)
    rating_ceiling: Mapped[str | None] = mapped_column(String, nullable=True)
    mood_seed: Mapped[str | None] = mapped_column(String, nullable=True)
    max_runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)  # WN-11
    deck: Mapped[list] = mapped_column(JSON, default=list)  # content_ids in the deck
    status: Mapped[str] = mapped_column(String, default="lobby")  # lobby|swiping|complete
    result: Mapped[list | None] = mapped_column(JSON, nullable=True)  # cached match result
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    participants: Mapped[list["GuestParticipant"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    swipes: Mapped[list["SwipeRecord"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class GuestParticipant(Base):
    """A session participant — registered user or accountless guest (WN-01)."""

    __tablename__ = "guest_participants"

    participant_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("watch_sessions.session_id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)  # null for guests
    display_name: Mapped[str] = mapped_column(String)
    completed: Mapped[bool] = mapped_column(default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["WatchSession"] = relationship(back_populates="participants")


class SwipeRecord(Base):
    __tablename__ = "swipe_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("watch_sessions.session_id", ondelete="CASCADE"), index=True
    )
    participant_id: Mapped[str] = mapped_column(String, index=True)
    content_id: Mapped[str] = mapped_column(String)
    signal: Mapped[str] = mapped_column(String)  # pass | interested | strong_yes
    swiped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    session: Mapped["WatchSession"] = relationship(back_populates="swipes")
