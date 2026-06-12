"""Profile, ratings, and Movie DNA routes (PRD §5.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MovieDNA, Rating, User
from app.schemas.models import (
    MovieDNAPublic,
    ProfileUpdate,
    RatingCreate,
    RatingPublic,
    UserPublic,
)
from app.security import get_current_user
from app.services.profile_service import recompute_dna

router = APIRouter(tags=["profiles"])


@router.get("/me", response_model=UserPublic)
def get_me(current: User = Depends(get_current_user)) -> User:
    return current


@router.patch("/me", response_model=UserPublic)
def update_me(
    body: ProfileUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current, field, value)
    db.commit()
    db.refresh(current)
    return current


@router.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: str, db: Session = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.get("/users/{user_id}/dna", response_model=MovieDNAPublic)
def get_dna(user_id: str, db: Session = Depends(get_db)) -> MovieDNA:
    dna = db.get(MovieDNA, user_id)
    if not dna:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "DNA not found")
    return dna


@router.post("/ratings", response_model=RatingPublic, status_code=status.HTTP_201_CREATED)
def create_rating(
    body: RatingCreate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Rating:
    """Upsert a rating, then recompute the user's Movie DNA (PRD MD-01)."""
    existing = db.scalar(
        select(Rating).where(
            Rating.user_id == current.user_id, Rating.content_id == body.content_id
        )
    )
    if existing:
        existing.signal = body.signal
        existing.source = body.source
        existing.genres = body.genres
        rating = existing
    else:
        rating = Rating(
            user_id=current.user_id,
            content_id=body.content_id,
            content_type=body.content_type,
            signal=body.signal,
            source=body.source,
            genres=body.genres,
        )
        db.add(rating)
    db.flush()
    recompute_dna(db, current)  # incremental refresh (PRD AI-04)
    db.commit()
    db.refresh(rating)
    return rating


@router.get("/ratings", response_model=list[RatingPublic])
def list_ratings(
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Rating]:
    return list(
        db.scalars(select(Rating).where(Rating.user_id == current.user_id)).all()
    )
