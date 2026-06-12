"""Pydantic request/response schemas for the API surface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Signal = Literal["love", "like", "dislike", "want"]
Intent = Literal["friends", "dating", "both", "off"]
SwipeSignal = Literal["pass", "interested", "strong_yes"]


# --- Auth -------------------------------------------------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str
    social_intent: Intent = "off"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Profile ----------------------------------------------------------------
class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    display_name: str
    bio: str
    avatar_url: str | None
    social_intent: Intent
    is_premium: bool


class MovieDNAPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    genre_weights: dict[str, float]
    fav_actors: list[str]
    fav_directors: list[str]
    pref_languages: list[str]
    pref_countries: list[str]
    rating_count: int
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    social_intent: Intent | None = None
    visible_to_matching: bool | None = None


# --- Ratings ----------------------------------------------------------------
class RatingCreate(BaseModel):
    content_id: str
    content_type: Literal["movie", "series"] = "movie"
    signal: Signal
    source: Literal["swipe", "manual", "import", "post_watch"] = "manual"
    # Optional genre metadata so DNA can be recomputed without a TMDB call.
    genres: list[str] = Field(default_factory=list)


class RatingPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rating_id: str
    content_id: str
    content_type: str
    signal: Signal
    source: str
    rated_at: datetime


# --- Compatibility ----------------------------------------------------------
class CompatibilityComponents(BaseModel):
    genre_overlap: float
    favourite_overlap: float
    rating_correlation: float
    watchlist_overlap: float


class CompatibilityResult(BaseModel):
    user_a: str
    user_b: str
    score: float
    components: CompatibilityComponents
    eligible: bool  # both users meet the 20-rating gate


class DiscoverProfile(BaseModel):
    user: UserPublic
    score: float
    shared_favourites: list[str]


# --- Watch Night ------------------------------------------------------------
class SessionCreate(BaseModel):
    services: list[str] = Field(default_factory=list)
    rating_ceiling: str | None = None
    mood_seed: str | None = None
    max_runtime: int | None = None
    deck: list[str] = Field(default_factory=list)


class JoinRequest(BaseModel):
    display_name: str
    user_id: str | None = None  # set for registered users


class ParticipantPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    participant_id: str
    display_name: str
    completed: bool


class SessionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    join_code: str
    status: str
    services: list[str]
    deck: list[str]
    participants: list[ParticipantPublic] = []


class SwipeCreate(BaseModel):
    participant_id: str
    content_id: str
    signal: SwipeSignal


class MatchPick(BaseModel):
    content_id: str
    aggregate_score: int
    full_consensus: bool
    positive_count: int
    total_participants: int
    dissenters: list[str]
    fallback_score: float


class SessionResult(BaseModel):
    session_id: str
    picks: list[MatchPick]
