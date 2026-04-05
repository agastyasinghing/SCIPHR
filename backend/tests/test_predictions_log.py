"""
Test: every successful POST /predict call inserts a row into predictions_log.

This is non-negotiable per CLAUDE.md ("Every prediction gets logged").

The test uses FastAPI TestClient with the predictor mocked (same pattern as
test_p0.py) but adds a real SQLite in-memory DB for the predictions_log table.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.models import Base
from intelligence.models import IntelligenceResult, ValueBetResult


@pytest.fixture
def client_with_db(engine):
    """
    TestClient wired to a real SQLite engine so predictions_log INSERTs
    are actually executed and verifiable.
    """
    from fastapi.testclient import TestClient

    mock_predict_result = {
        "fighter1": "Jon Jones",
        "fighter2": "Stipe Miocic",
        "winner": "Jon Jones",
        "confidence": 0.72,
        "prob_fighter1": 0.72,
        "prob_fighter2": 0.28,
        "fighter1_stats": {
            "wins_total": 27, "losses_total": 1, "draw": 0,
            "SLpM_total": 4.5, "sig_str_acc_total": 57,
            "sig_str_def_total": 64, "td_avg_total": 1.9,
            "td_acc_total": 44, "td_def_total": 96,
            "sub_avg_total": 0.5, "age": 36,
            "height": 193.0, "reach": 215.0, "weight": 265.0,
            "weight_class": "Heavyweight",
        },
        "fighter2_stats": {
            "wins_total": 20, "losses_total": 4, "draw": 0,
            "SLpM_total": 3.9, "sig_str_acc_total": 52,
            "sig_str_def_total": 58, "td_avg_total": 0.4,
            "td_acc_total": 37, "td_def_total": 71,
            "sub_avg_total": 0.1, "age": 40,
            "height": 193.0, "reach": 198.0, "weight": 265.0,
            "weight_class": "Heavyweight",
        },
    }

    mock_predictor = MagicMock()
    mock_predictor.predict_fight.return_value = mock_predict_result
    mock_predictor.feature_calculator.get_latest_fighter_stats.return_value = (
        mock_predict_result["fighter1_stats"]
    )

    mock_orchestrator = MagicMock()
    mock_orchestrator.compute.return_value = IntelligenceResult(value_bet=ValueBetResult())

    import main as app_module
    app_module.engine = engine   # inject real SQLite engine before TestClient

    with patch("main.predictor", mock_predictor), \
         patch("main.orchestrator", mock_orchestrator), \
         patch("main.ai_analyst") as mock_ai:
        mock_ai.generate_fight_analysis.return_value = {"summary": "Test analysis"}
        from main import app
        # Use TestClient without context manager (same as test_p0.py) so the
        # startup event does not run — engine and predictor are already injected.
        yield TestClient(app), engine


def test_predict_logs_to_predictions_log(client_with_db):
    """
    A successful /predict call must insert exactly one row into predictions_log.
    """
    client, db_engine = client_with_db

    # Confirm table is empty before the request
    with db_engine.connect() as conn:
        count_before = conn.execute(
            text("SELECT COUNT(*) FROM predictions_log")
        ).scalar()
    assert count_before == 0

    resp = client.post("/predict", json={"fighter1": "Jon Jones", "fighter2": "Stipe Miocic"})
    assert resp.status_code == 200

    with db_engine.connect() as conn:
        count_after = conn.execute(
            text("SELECT COUNT(*) FROM predictions_log")
        ).scalar()
        row = conn.execute(
            text("SELECT fighter1, fighter2, winner, confidence FROM predictions_log LIMIT 1")
        ).fetchone()

    assert count_after == 1
    assert row[0] == "Jon Jones"
    assert row[1] == "Stipe Miocic"
    assert row[2] == "Jon Jones"
    assert abs(row[3] - 0.72) < 0.001
