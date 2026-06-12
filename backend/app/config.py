"""Application settings (12-factor, env-driven)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CINEMATCH_", extra="ignore")

    # --- App ---
    app_name: str = "CineMatch API"
    environment: str = "development"
    debug: bool = True

    # --- Persistence ---
    # Defaults to local SQLite so the service runs with zero infra; point at
    # Postgres in any real environment (see docker-compose.yml / .env.example).
    database_url: str = "sqlite:///./cinematch.db"
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth (JWT / OAuth2, PRD §6.1) ---
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 60 * 24 * 7

    # --- External integrations (PRD §6.1 / §13) ---
    tmdb_api_key: str = ""
    justwatch_enabled: bool = False
    streaming_cache_ttl_seconds: int = 60 * 60 * 24  # 24h TTL (PRD risk table)

    # --- Model weights (overridable for experiments, PRD §14.6) ---
    weight_genre_overlap: float = 0.30
    weight_favourite_overlap: float = 0.35
    weight_rating_correlation: float = 0.25
    weight_watchlist_overlap: float = 0.10

    @property
    def compatibility_weights(self) -> dict[str, float]:
        return {
            "genre_overlap": self.weight_genre_overlap,
            "favourite_overlap": self.weight_favourite_overlap,
            "rating_correlation": self.weight_rating_correlation,
            "watchlist_overlap": self.weight_watchlist_overlap,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
