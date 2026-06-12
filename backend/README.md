# CineMatch Backend (v1 MVP)

Backend service for **CineMatch — social discovery through shared taste**, built
from `CineMatch_PRD_v1`. This is the first build increment: the full backend
scaffold (FastAPI) matching the PRD §6 architecture, with the core algorithms
from PRD §7 and §14 fully implemented and unit-tested.

## What's implemented

| Area | PRD ref | Status |
|------|---------|--------|
| Movie DNA computation (genre weights, signals, snapshot) | §14.1 | ✅ Core + tests |
| Compatibility score (4-signal weighted composite) | §7 / §14.3 | ✅ Core + tests |
| Watch Night matching engine (consensus + partial fallback) | §14.2 | ✅ Core + tests |
| Recommendation engine (hybrid blend, paired, levers) | §14.4 / §14.5 | ✅ Core + tests |
| Auth (signup/login, JWT) | §6.1 / §8.1 | ✅ |
| Profiles + ratings API, incremental DNA refresh | §5.1 | ✅ |
| Social discovery, compatibility, connect/block | §5.3 | ✅ |
| Watch Night sessions + WebSocket result push | §5.2 | ✅ |
| Data models / Postgres schema | §6.2 | ✅ (SQLAlchemy) |
| TMDB / JustWatch integration layer | §6.1 / §13 | 🟡 Scaffold (deep-links live, availability stubbed) |
| Recommendation home feed (catalogue feature store) | §5.4 | 🟡 Paired + alpha live; full feed needs TMDB catalogue |

Deferred to later increments: mobile/web clients, AI conversation starters
(LLM), community lists/clubs, premium billing, Alembic migration history.

## Architecture (PRD §6.1)

```
app/
  core/           # Pure, dependency-free algorithms (PRD §7 & §14)
    weights.py        # config-driven weights + tuning levers
    movie_dna.py      # genre weights, rating signals, DNA snapshot
    compatibility.py  # 4-signal composite score
    matching.py       # Watch Night consensus engine
    recommendations.py# hybrid CF + content blend, paired recs
  models/         # SQLAlchemy ORM = the Postgres schema (PRD §6.2)
  schemas/        # Pydantic request/response models
  services/       # Bridge ORM <-> core algorithms
  api/            # FastAPI routers (auth, profiles, social, sessions, recs)
  integrations/   # TMDB / JustWatch layer
  realtime.py     # Watch Night WebSocket hub
  main.py         # App wiring (API Gateway)
tests/            # Unit tests for core + API smoke tests
```

The `core/` package has **no framework or DB coupling** — every algorithm is
pure and unit-tested in isolation, per the PRD's explainable/tunable/debuggable
design philosophy (§14.6).

## Quickstart

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest -q

# Run the API (SQLite, zero infra)
uvicorn app.main:app --reload
# -> http://localhost:8000/docs
```

### With Postgres + Redis

```bash
docker compose up --build
# API on :8000, Postgres on :5432, Redis on :6379
```

## Configuration

All settings are env vars prefixed `CINEMATCH_` (see `.env.example`). Model
weights and tuning levers are config values (PRD §14.6) so the product team can
run experiments without code changes.

## Tuning levers (PRD §14.5)

- **Recency bias (λ)** — how fast old ratings lose influence.
- **Diversity injection (δ)** — accuracy vs novelty in recommendations.
- **Social weight (α override)** — personal vs taste-neighbour blend.

## Next increments

1. TMDB catalogue ingestion + feature store → full personalised home feed (§5.4).
2. Alembic migrations + Postgres-backed `CompatibilityEdge` precompute (OQ-06).
3. AI conversation starters + mood-based semantic search (§5.4, AI-03/AI-04).
4. Client apps (iOS / Android / Web) against this API.
```
