"""
Tests for Phase 3 API Layer — FastAPI endpoint wiring.

Covers new codepaths introduced in Phase 3:
  [1]  /predict: intelligence field always present in response
  [2]  /predict: fight_id provided → orchestrator.compute receives event_fight
  [3]  /predict: fight_id=None → orchestrator.compute receives event_fight=None
  [4]  /predict: orchestrator returns empty IntelligenceResult → response still valid
  [5]  GET /health: db ok + model loaded → 200 {"status": "ok"}
  [6]  GET /health: engine raises on SELECT 1 → 503 {"status": "degraded"}
  [7]  GET /health: predictor is None → 503 {"status": "degraded", "model": "not_loaded"}
  [8]  GET /events: returns event list from in-memory events_data
  [9]  GET /events/{id}: valid fight_id → returns fight dict
  [10] GET /events/{id}: invalid fight_id → 404
  [11] _load_events(): missing events.json → RuntimeError
  [12] IntelligenceResult.model_dump() → JSON-serialisable (no numpy types)

Setup:
  - startup_event is cleared at module import to prevent real DB/model loading.
  - App globals (engine, predictor, orchestrator, events_data, events_index)
    are set directly in the client fixture before each test.
  - ai_analyst.generate_fight_analysis is mocked to avoid Claude API calls.
"""

import json
import sys
import os

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as app_module
from main import app, _load_events
from intelligence.models import IntelligenceResult, ValueBetResult

# Clear startup/shutdown handlers at import time so TestClient never tries
# to connect to a real DB or load the XGBoost model.
app.router.on_startup.clear()
app.router.on_shutdown.clear()


# ── Test data ─────────────────────────────────────────────────────────────────

_SAMPLE_PREDICT_RESULT = {
    'fighter1': 'Fighter A',
    'fighter2': 'Fighter B',
    'prob_fighter1': 0.65,
    'prob_fighter2': 0.35,
    'winner': 'Fighter A',
    'confidence': 0.65,
    'fighter1_stats': {'wins': 18, 'losses': 3},
    'fighter2_stats': {'wins': 14, 'losses': 4},
}

_SAMPLE_FIGHT = {
    'fight_id': 1,
    'fighter1_name': 'Fighter A',
    'fighter2_name': 'Fighter B',
    'is_title_fight': True,
    'short_notice': False,
    'weight_miss': False,
    'narratives': ['HYPE_TRAIN'],
    'weight_class': 'Lightweight',
    'card_position': 'main_event',
}

_SAMPLE_EVENTS_DATA = {
    'events': [
        {
            'event_id': 1,
            'event_name': 'UFC Test Event',
            'date': '2024-04-13',
            'location': 'Las Vegas, NV',
            'fights': [_SAMPLE_FIGHT],
        }
    ]
}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_predictor():
    m = MagicMock()
    m.predict_fight.return_value = dict(_SAMPLE_PREDICT_RESULT)
    return m


@pytest.fixture
def mock_orchestrator():
    m = MagicMock()
    m.compute.return_value = IntelligenceResult(value_bet=ValueBetResult())
    return m


@pytest.fixture
def client(engine, mock_predictor, mock_orchestrator):
    """
    TestClient with all app globals set for testing.

    Startup is cleared at module level — globals are set directly here
    instead of running the real startup_event. ai_analyst is mocked
    to prevent Claude API calls during tests.
    """
    app_module.engine = engine
    app_module.predictor = mock_predictor
    app_module.orchestrator = mock_orchestrator
    app_module.events_data = _SAMPLE_EVENTS_DATA
    app_module.events_index = {1: _SAMPLE_FIGHT}

    with patch.object(app_module.ai_analyst, 'generate_fight_analysis', return_value={"analysis": "test"}):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

    # Reset globals after each test to prevent state leakage
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None
    app_module.events_data = {'events': []}
    app_module.events_index = {}


# ── /predict tests ────────────────────────────────────────────────────────────

class TestPredict:
    def test_predict_returns_intelligence_field(self, client):
        """[1] /predict response always contains 'intelligence' key."""
        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        body = resp.json()
        assert "intelligence" in body
        assert isinstance(body["intelligence"], dict)

    def test_predict_with_fight_id_passes_event_fight(self, client, mock_orchestrator):
        """[2] fight_id=1 → orchestrator.compute receives matching event_fight dict."""
        resp = client.post(
            "/predict",
            json={"fighter1": "Fighter A", "fighter2": "Fighter B", "fight_id": 1},
        )
        assert resp.status_code == 200
        call_kwargs = mock_orchestrator.compute.call_args.kwargs
        assert call_kwargs["fight_id"] == 1
        assert call_kwargs["event_fight"] == _SAMPLE_FIGHT

    def test_predict_without_fight_id_passes_no_event_context(self, client, mock_orchestrator):
        """[3] fight_id=None → orchestrator.compute called with event_fight=None."""
        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        call_kwargs = mock_orchestrator.compute.call_args.kwargs
        assert call_kwargs["fight_id"] is None
        assert call_kwargs["event_fight"] is None

    def test_predict_empty_intelligence_still_succeeds(self, client, mock_orchestrator):
        """[4] orchestrator returns empty IntelligenceResult → response is still valid."""
        mock_orchestrator.compute.return_value = IntelligenceResult()  # all modules None
        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        body = resp.json()
        assert "intelligence" in body
        # All optional modules are None in an empty IntelligenceResult
        assert body["intelligence"]["chaos"] is None
        # value_bet is never None — always has at minimum NO_ODDS signal
        assert body["intelligence"]["value_bet"] is not None
        assert body["intelligence"]["value_bet"]["signal"] == "NO_ODDS"


# ── /health tests ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        """[5] DB reachable + model loaded → 200 {"status": "ok"}."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["model"] == "loaded"

    def test_health_db_down(self, client):
        """[6] engine.connect() raises → 503 {"status": "degraded", "db": "error"}."""
        bad_engine = MagicMock()
        bad_engine.connect.side_effect = Exception("Connection refused")
        app_module.engine = bad_engine

        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["db"] == "error"
        assert body["model"] == "loaded"

    def test_health_model_not_loaded(self, client):
        """[7] predictor is None → 503 {"status": "degraded", "model": "not_loaded"}."""
        app_module.predictor = None

        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["model"] == "not_loaded"


# ── /events tests ─────────────────────────────────────────────────────────────

class TestEvents:
    def test_events_returns_list(self, client):
        """[8] GET /events returns the full events list."""
        resp = client.get("/events")
        assert resp.status_code == 200
        body = resp.json()
        assert "events" in body
        assert len(body["events"]) == 1
        assert body["events"][0]["event_name"] == "UFC Test Event"

    def test_events_fight_id_found(self, client):
        """[9] GET /events/1 returns the matching fight dict."""
        resp = client.get("/events/1")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fight_id"] == 1
        assert body["fighter1_name"] == "Fighter A"
        assert body["narratives"] == ["HYPE_TRAIN"]

    def test_events_fight_id_not_found(self, client):
        """[10] GET /events/999 → 404 when fight_id not in events_index."""
        resp = client.get("/events/999")
        assert resp.status_code == 404


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestLoadEvents:
    def test_load_events_missing_file_raises(self, tmp_path, monkeypatch):
        """[11] _load_events() raises RuntimeError when events.json is absent."""
        # Point __file__ to tmp_path (no events/ subdirectory there)
        monkeypatch.setattr(app_module, '__file__', str(tmp_path / "main.py"))
        with pytest.raises(RuntimeError, match="events/events.json not found"):
            _load_events()


class TestIntelligenceResultSerialization:
    def test_intelligence_result_json_serializable(self):
        """[12] IntelligenceResult.model_dump() produces JSON-serialisable output."""
        result = IntelligenceResult(value_bet=ValueBetResult())
        dumped = result.model_dump()
        # json.dumps raises TypeError if any value is not serialisable (e.g. numpy types)
        serialized = json.dumps(dumped)
        parsed = json.loads(serialized)
        assert parsed["value_bet"]["signal"] == "NO_ODDS"
        assert parsed["chaos"] is None
        assert parsed["badges"] == []
