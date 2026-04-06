"""
Tests for GET /historical-scorecard endpoint.

Phase 4 — endpoint exists but predictions_log is empty at launch.
Tests verify: 200 response, correct schema, empty state, and
row rendering when data exists.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as app_module
from main import app

# Clear startup so tests don't try to connect to a real DB
app.router.on_startup.clear()


@pytest.fixture
def client():
    """Minimal TestClient — each test patches main.engine directly."""
    app_module.engine = None  # will be patched per-test
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def make_mock_row(
    id=1,
    fighter1="Jon Jones",
    fighter2="Stipe Miocic",
    winner="Jon Jones",
    confidence=0.72,
    prob_f1=0.72,
    prob_f2=0.28,
    actual_winner=None,
    value_signal=None,
    edge_pct=None,
    created_at=None,
):
    from datetime import datetime
    row = MagicMock()
    row.id = id
    row.fighter1 = fighter1
    row.fighter2 = fighter2
    row.winner = winner
    row.confidence = confidence
    row.prob_f1 = prob_f1
    row.prob_f2 = prob_f2
    row.actual_winner = actual_winner
    row.value_signal = value_signal
    row.edge_pct = edge_pct
    row.created_at = created_at or datetime(2026, 4, 1, 10, 0, 0)
    return row


class TestHistoricalScorecardEndpoint:
    def test_returns_200_empty(self, client):
        """Endpoint returns 200 with empty predictions when log is empty."""
        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),  # count query
                MagicMock(fetchall=MagicMock(return_value=[])),  # rows query
            ]
            response = client.get("/historical-scorecard")

        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert data["predictions"] == []
        assert data["total"] == 0
        assert data["accuracy"] is None

    def test_returns_predictions_when_data_exists(self, client):
        """Endpoint returns prediction rows with correct field mapping."""
        row = make_mock_row(actual_winner=None)

        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=1)),
                MagicMock(fetchall=MagicMock(return_value=[row])),
            ]
            response = client.get("/historical-scorecard")

        assert response.status_code == 200
        data = response.json()
        assert len(data["predictions"]) == 1
        pred = data["predictions"][0]
        assert pred["fighter1"] == "Jon Jones"
        assert pred["fighter2"] == "Stipe Miocic"
        assert pred["predicted_winner"] == "Jon Jones"
        assert abs(pred["confidence"] - 0.72) < 0.001
        assert pred["actual_winner"] is None
        assert pred["correct"] is None  # unresolved

    def test_correct_flag_true_when_prediction_matches_actual(self, client):
        """correct=True when predicted_winner == actual_winner."""
        row = make_mock_row(winner="Jon Jones", actual_winner="Jon Jones")

        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=1)),
                MagicMock(fetchall=MagicMock(return_value=[row])),
            ]
            response = client.get("/historical-scorecard")

        pred = response.json()["predictions"][0]
        assert pred["correct"] is True

    def test_correct_flag_false_when_prediction_wrong(self, client):
        """correct=False when predicted_winner != actual_winner."""
        row = make_mock_row(winner="Jon Jones", actual_winner="Stipe Miocic")

        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=1)),
                MagicMock(fetchall=MagicMock(return_value=[row])),
            ]
            response = client.get("/historical-scorecard")

        pred = response.json()["predictions"][0]
        assert pred["correct"] is False

    def test_accuracy_computed_from_resolved_rows(self, client):
        """accuracy = resolved correct / total resolved (as a percentage)."""
        rows = [
            make_mock_row(id=1, winner="Jon Jones", actual_winner="Jon Jones"),
            make_mock_row(id=2, fighter1="Islam Makhachev", fighter2="Charles Oliveira",
                          winner="Islam Makhachev", actual_winner="Charles Oliveira"),
        ]

        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=2)),
                MagicMock(fetchall=MagicMock(return_value=rows)),
            ]
            response = client.get("/historical-scorecard")

        data = response.json()
        assert data["accuracy"] == 50.0  # 1/2 correct
        assert data["resolved_count"] == 2

    def test_pagination_params_passed_through(self, client):
        """limit and offset are echoed back in the response."""
        with patch("main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.side_effect = [
                MagicMock(scalar=MagicMock(return_value=0)),
                MagicMock(fetchall=MagicMock(return_value=[])),
            ]
            response = client.get("/historical-scorecard?limit=10&offset=20")

        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20
