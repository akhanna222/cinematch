"""End-to-end API smoke tests covering the core v1 flows."""

from tests.conftest import register


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_signup_login_and_me(client):
    headers, user_id = register(client, "a@example.com", "Ava")
    me = client.get("/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Ava"


def test_rating_updates_dna(client):
    headers, user_id = register(client, "b@example.com", "Ben")
    client.post(
        "/ratings",
        headers=headers,
        json={"content_id": "603", "signal": "love", "genres": ["thriller"]},
    )
    dna = client.get(f"/users/{user_id}/dna").json()
    assert dna["rating_count"] == 1
    assert dna["genre_weights"]["thriller"] == 1.0


# Deterministic varied pattern so rating_correlation (Pearson) is exercised —
# all-identical signals would give zero variance and an undefined correlation.
_PATTERN = ["love", "like", "dislike"]


def _seed_ratings(client, headers, n=20, offset=0, genre="thriller", vary=True):
    for i in range(n):
        signal = _PATTERN[i % len(_PATTERN)] if vary else "love"
        client.post(
            "/ratings",
            headers=headers,
            json={"content_id": f"m{offset + i}", "signal": signal, "genres": [genre]},
        )


def test_compatibility_and_discover(client):
    h1, u1 = register(client, "c1@example.com", "Cy")
    h2, u2 = register(client, "c2@example.com", "Dee")

    # Both rate the same 20 thriller titles with the same varied signals, plus
    # a shared watchlist -> all four compatibility components fire high.
    _seed_ratings(client, h1, n=20, genre="thriller")
    _seed_ratings(client, h2, n=20, genre="thriller")
    for h in (h1, h2):
        client.post("/ratings", headers=h,
                    json={"content_id": "wl1", "signal": "want", "genres": ["thriller"]})

    comp = client.get(f"/social/compatibility/{u2}", headers=h1).json()
    assert comp["eligible"] is True
    assert comp["score"] > 0.9

    feed = client.get("/social/discover", headers=h1).json()
    assert any(p["user"]["user_id"] == u2 for p in feed)


def test_below_gate_not_in_discover(client):
    h1, u1 = register(client, "g1@example.com", "Gus")
    h2, u2 = register(client, "g2@example.com", "Hal")
    _seed_ratings(client, h1, n=20)
    _seed_ratings(client, h2, n=5)  # below the 20-rating gate

    feed = client.get("/social/discover", headers=h1).json()
    assert all(p["user"]["user_id"] != u2 for p in feed)


def test_mutual_connection(client):
    h1, u1 = register(client, "m1@example.com", "Mo")
    h2, u2 = register(client, "m2@example.com", "Nia")

    r1 = client.post(f"/social/connect/{u2}", headers=h1).json()
    assert r1["mutual"] is False
    r2 = client.post(f"/social/connect/{u1}", headers=h2).json()
    assert r2["mutual"] is True


def test_watch_night_end_to_end(client):
    # Host creates a session with a 3-title deck.
    create = client.post(
        "/sessions",
        json={"services": ["netflix"], "deck": ["dune", "barbie", "oppenheimer"]},
    )
    assert create.status_code == 201
    session_id = create.json()["session_id"]
    code = create.json()["join_code"]

    # Two guests join (no account).
    j1 = client.post(f"/sessions/join/{code}", json={"display_name": "Guest1"}).json()
    j2 = client.post(f"/sessions/join/{code}", json={"display_name": "Guest2"}).json()
    p1, p2 = j1["participant_id"], j2["participant_id"]

    client.post(f"/sessions/{session_id}/start")

    # Both love 'dune'; split on the others.
    for pid in (p1, p2):
        client.post(
            f"/sessions/{session_id}/swipe",
            json={"participant_id": pid, "content_id": "dune", "signal": "strong_yes"},
        )
    client.post(
        f"/sessions/{session_id}/swipe",
        json={"participant_id": p1, "content_id": "barbie", "signal": "interested"},
    )

    client.post(f"/sessions/{session_id}/complete/{p1}")
    final = client.post(f"/sessions/{session_id}/complete/{p2}").json()

    assert final["complete"] is True
    assert final["picks"][0]["content_id"] == "dune"
    assert final["picks"][0]["full_consensus"] is True
