"""Pytest fixtures: isolated SQLite DB + FastAPI test client.

Environment is configured *before* any app import so the cached settings
pick up the throwaway database.
"""

import os
import tempfile

import pytest

# Point the app at a throwaway SQLite file before app modules import settings.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["CINEMATCH_DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ["CINEMATCH_JWT_SECRET"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine, init_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Recreate all tables before each test for isolation."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def register(client, email, name, intent="both"):
    """Helper: sign up + log in, returning auth headers and user id."""
    r = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "display_name": name,
              "social_intent": intent},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["user_id"]
    tok = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert tok.status_code == 200, tok.text
    headers = {"Authorization": f"Bearer {tok.json()['access_token']}"}
    return headers, user_id
