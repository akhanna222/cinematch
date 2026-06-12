"""User, Movie DNA, and Rating models (PRD §6.2)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str] = mapped_column(String)
    bio: Mapped[str] = mapped_column(String, default="")
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # friends | dating | both | off
    social_intent: Mapped[str] = mapped_column(String, default="off")
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    # Privacy controls (SM-07).
    visible_to_matching: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    dna: Mapped["MovieDNA"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    streaming_subs: Mapped[list["StreamingSub"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class MovieDNA(Base):
    __tablename__ = "movie_dna"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    genre_weights: Mapped[dict] = mapped_column(JSON, default=dict)  # {'thriller': 0.82}
    fav_actors: Mapped[list] = mapped_column(JSON, default=list)  # TMDB person IDs
    fav_directors: Mapped[list] = mapped_column(JSON, default=list)
    pref_languages: Mapped[list] = mapped_column(JSON, default=list)
    pref_countries: Mapped[list] = mapped_column(JSON, default=list)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="dna")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (UniqueConstraint("user_id", "content_id", name="uq_user_content"),)

    rating_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    content_id: Mapped[str] = mapped_column(String, index=True)  # TMDB id
    content_type: Mapped[str] = mapped_column(String, default="movie")  # movie | series
    signal: Mapped[str] = mapped_column(String)  # love | like | dislike | want
    source: Mapped[str] = mapped_column(String, default="manual")  # swipe|manual|import|post_watch
    # Genre tags captured at ingest so DNA can be recomputed without a TMDB call.
    genres: Mapped[list] = mapped_column(JSON, default=list)
    rated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="ratings")


class StreamingSub(Base):
    __tablename__ = "streaming_subs"
    __table_args__ = (UniqueConstraint("user_id", "service", name="uq_user_service"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    service: Mapped[str] = mapped_column(String)  # netflix | prime | appletv | disney | max

    user: Mapped["User"] = relationship(back_populates="streaming_subs")


# Float imported for forward-compat with future numeric columns.
_ = Float
