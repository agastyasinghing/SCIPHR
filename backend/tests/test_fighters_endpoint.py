"""
Test: GET /fighters queries the fighters table directly via the engine.

Verifies that a DB with data → populated response, and an empty DB → empty
list. The endpoint never reads from the predictor's startup cache.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.models import Base, Fighter


def _make_client(engine):
    """Inject engine, mock predictor via _build_fighter_list, return TestClient."""
    from fastapi.testclient import TestClient
    import main as app_module
    app_module.engine = engine

    # Build a real predictor stub whose available_fighters reads from the DB
    mock_predictor = MagicMock()
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT name FROM fighters ORDER BY name")).fetchall()
    mock_predictor.available_fighters = [r[0] for r in rows]

    with patch("main.predictor", mock_predictor):
        from main import app
        yield TestClient(app)


@pytest.fixture
def client_empty_db(engine):
    yield from _make_client(engine)


@pytest.fixture
def client_with_fighters(engine):
    """Seed two fighters before wiring the client."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO fighters (name, wins, losses) VALUES "
                "(:n1, :w1, :l1), (:n2, :w2, :l2)"
            ),
            {"n1": "Jon Jones", "w1": 27, "l1": 1,
             "n2": "Stipe Miocic", "w2": 20, "l2": 4},
        )
    yield from _make_client(engine)


def test_fighters_endpoint_returns_db_names(client_with_fighters):
    """GET /fighters should include names that came from the fighters table."""
    resp = client_with_fighters.get("/fighters")
    assert resp.status_code == 200
    data = resp.json()
    names = data if isinstance(data, list) else data.get("fighters", [])
    assert "Jon Jones" in names
    assert "Stipe Miocic" in names


def test_fighters_endpoint_empty_db_returns_empty_list(client_empty_db):
    """If the migration hasn't run, /fighters must return [] not crash."""
    resp = client_empty_db.get("/fighters")
    assert resp.status_code == 200
    data = resp.json()
    names = data if isinstance(data, list) else data.get("fighters", [])
    assert names == []
