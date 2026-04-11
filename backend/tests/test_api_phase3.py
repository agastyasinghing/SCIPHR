"""
Tests for Phase 3 API Layer — FastAPI endpoint wiring.

Covers new codepaths introduced in Phase 3:
  [1]  /predict: intelligence field always present in response
  [2]  /predict: fight_id provided → orchestrator.compute receives event_fight
  [3]  /predict: fight_id=None → orchestrator.compute receives event_fight=None
  [4]  /predict: orchestrator returns empty IntelligenceResult → response still valid
  [5]  GET /health: db ok + model loaded → 200 {"status": "ok", "redis_connected": "not_configured"}
  [6]  GET /health: engine raises on SELECT 1 → 503 {"status": "degraded"}
  [7]  GET /health: predictor is None → 503 {"status": "degraded", "model": "not_loaded"}
  [8]  GET /events: returns event list from in-memory events_data
  [9]  GET /events/{event_id}: valid event_id → returns full event card
  [10] GET /events/{event_id}: invalid event_id → 404
  [11] _load_events(): missing events.json → RuntimeError
  [12] IntelligenceResult.model_dump() → JSON-serialisable (no numpy types)
  [13] /predict: ai_analysis is null (async — not generated inline)
  [14] /predict: odds_at_prediction logged when value_bet has implied probs
  [15] POST /predict/simple: returns winner + confidence, no intelligence field
  [16] POST /predict/simple: same-fighter → 400
  [17] GET /events/upcoming: returns the soonest event by date
  [18] GET /events/upcoming: falls back to most recent past event
  [19] GET /fighter/{name}/history: returns fight list from DB
  [20] POST /generate-ai-analysis: returns analysis dict
  [21] POST /generate-ai-analysis: rate limit 429 on 4th request
  [22] GET /fighter/{name}/history: blue-corner (b_name) path returns correct result/opponent
  [23-27] Input sanitization: >100-char names + non-printable chars → 422; whitespace stripped

Setup:
  - startup_event is cleared at module import to prevent real DB/model loading.
  - App globals (engine, predictor, orchestrator, events_data, events_index,
    events_by_id) are set directly in the client fixture before each test.
  - ai_analyst.generate_fight_analysis is not mocked for /predict (no longer called).
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
    # Return None by default so fuzzy matching is skipped in history endpoint.
    # Tests that need a specific match can override this explicitly.
    m.search_fighter.return_value = None
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
    instead of running the real startup_event.
    """
    app_module.engine = engine
    app_module.predictor = mock_predictor
    app_module.orchestrator = mock_orchestrator
    app_module.events_data = _SAMPLE_EVENTS_DATA
    app_module.events_index = {1: _SAMPLE_FIGHT}
    app_module.events_by_id = {1: _SAMPLE_EVENTS_DATA["events"][0]}

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    # Reset globals after each test to prevent state leakage
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None
    app_module.events_data = {'events': []}
    app_module.events_index = {}
    app_module.events_by_id = {}


# ── /predict tests ────────────────────────────────────────────────────────────

class TestPredict:
    def test_predict_returns_intelligence_field(self, client):
        """[1] /predict response always contains 'intelligence' key."""
        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        body = resp.json()
        assert "intelligence" in body
        assert isinstance(body["intelligence"], dict)

    def test_predict_ai_analysis_is_null(self, client):
        """[13] /predict returns ai_analysis: null — Claude called async via /generate-ai-analysis."""
        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        body = resp.json()
        assert "ai_analysis" in body
        assert body["ai_analysis"] is None

    def test_predict_logs_odds_when_value_bet_has_probs(self, engine, client, mock_orchestrator):
        """[14] odds_at_prediction populated in predictions_log when value_bet has implied probs."""
        from intelligence.models import ValueBetResult
        from sqlalchemy import text

        mock_orchestrator.compute.return_value = IntelligenceResult(
            value_bet=ValueBetResult(
                signal="EDGE_DETECTED",
                active=True,
                implied_prob_f1=0.60,
                implied_prob_f2=0.40,
            )
        )

        resp = client.post("/predict", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT odds_at_prediction FROM predictions_log ORDER BY id DESC LIMIT 1")
            ).fetchone()

        assert row is not None
        import json as _json
        odds = _json.loads(row[0]) if isinstance(row[0], str) else row[0]
        assert odds is not None
        assert "Fighter A" in odds
        assert "Fighter B" in odds
        assert abs(odds["Fighter A"]["implied"] - 0.60) < 0.001

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
        """[5] DB reachable + model loaded → 200 with db_connected/model_loaded/redis_connected/version fields."""
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["db_connected"] == "ok"
        assert body["model_loaded"] == "loaded"
        # Redis not configured in test env — in-memory fallback is active.
        assert body["redis_connected"] == "not_configured"
        assert "version" in body

    def test_health_db_down(self, client):
        """[6] engine.connect() raises → 503 {"status": "degraded", "db_connected": "error"}."""
        bad_engine = MagicMock()
        bad_engine.connect.side_effect = Exception("Connection refused")
        app_module.engine = bad_engine

        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["db_connected"] == "error"
        assert body["model_loaded"] == "loaded"

    def test_health_model_not_loaded(self, client):
        """[7] predictor is None → 503 {"status": "degraded", "model_loaded": "not_loaded"}."""
        app_module.predictor = None

        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["model_loaded"] == "not_loaded"


# ── Input sanitization tests ──────────────────────────────────────────────────

class TestInputSanitization:
    """Verify _sanitize_fighter_name() enforcement on fighter name endpoints."""

    def test_predict_name_too_long_returns_422(self, client):
        """POST /predict with fighter1 > 100 chars → 422."""
        resp = client.post("/predict", json={
            "fighter1": "A" * 101,
            "fighter2": "Fighter B",
        })
        assert resp.status_code == 422

    def test_predict_nonprintable_char_returns_422(self, client):
        """POST /predict with NUL byte in fighter name → 422."""
        resp = client.post("/predict", json={
            "fighter1": "Jon\x00Jones",
            "fighter2": "Fighter B",
        })
        assert resp.status_code == 422

    def test_predict_simple_name_too_long_returns_422(self, client):
        """POST /predict/simple with fighter2 > 100 chars → 422."""
        resp = client.post("/predict/simple", json={
            "fighter1": "Fighter A",
            "fighter2": "B" * 101,
        })
        assert resp.status_code == 422

    def test_predict_simple_nonprintable_returns_422(self, client):
        """POST /predict/simple with control char in fighter name → 422."""
        resp = client.post("/predict/simple", json={
            "fighter1": "Fighter\x1bA",
            "fighter2": "Fighter B",
        })
        assert resp.status_code == 422

    def test_predict_strips_whitespace(self, client, mock_predictor, mock_orchestrator):
        """POST /predict with padded names → whitespace stripped before same-fighter check."""
        # "Fighter A" and "  Fighter A  " should be treated as the same fighter.
        resp = client.post("/predict", json={
            "fighter1": "Fighter A",
            "fighter2": "  Fighter A  ",
        })
        assert resp.status_code == 400  # same-fighter after strip


# ── CORS tests ────────────────────────────────────────────────────────────────

class TestCORS:
    def test_cors_allowed_origin_gets_header(self, client):
        """[23] CORS preflight with an allowed origin returns Access-Control-Allow-Origin."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_unlisted_origin_is_blocked(self, client):
        """[24] CORS does not echo back an origin that is not in ALLOWED_ORIGINS."""
        resp = client.options(
            "/health",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") != "https://evil.com"


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

    def test_events_event_id_found(self, client):
        """[9] GET /events/1 returns the full event card by event_id."""
        resp = client.get("/events/1")
        assert resp.status_code == 200
        body = resp.json()
        # Full event card — not a single fight
        assert body["event_id"] == 1
        assert body["event_name"] == "UFC Test Event"
        assert "fights" in body
        assert len(body["fights"]) == 1

    def test_events_event_id_not_found(self, client):
        """[10] GET /events/999 → 404 when event_id not in events_by_id."""
        resp = client.get("/events/999")
        assert resp.status_code == 404

    def test_events_upcoming_returns_next_event(self, client):
        """[17] GET /events/upcoming returns the soonest event."""
        resp = client.get("/events/upcoming")
        assert resp.status_code == 200
        body = resp.json()
        assert "event_name" in body
        assert "fights" in body

    def test_events_upcoming_no_events_returns_404(self, client):
        """[18] GET /events/upcoming → 404 when events list is empty."""
        app_module.events_data = {"events": []}
        resp = client.get("/events/upcoming")
        assert resp.status_code == 404


# ── /predict/simple tests ─────────────────────────────────────────────────────

class TestPredictSimple:
    def test_predict_simple_returns_winner_and_confidence(self, client):
        """[15] POST /predict/simple returns winner, confidence, probs — no intelligence."""
        resp = client.post("/predict/simple", json={"fighter1": "Fighter A", "fighter2": "Fighter B"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["winner"] == "Fighter A"
        assert "confidence" in body
        assert "prob_fighter1" in body
        assert "prob_fighter2" in body
        # No intelligence bundle in simple mode
        assert "intelligence" not in body
        assert "ai_analysis" not in body

    def test_predict_simple_same_fighter_returns_400(self, client):
        """[16] POST /predict/simple same fighter → 400."""
        resp = client.post("/predict/simple", json={"fighter1": "Fighter A", "fighter2": "Fighter A"})
        assert resp.status_code == 400


# ── /fighter/{name}/history tests ─────────────────────────────────────────────

class TestFighterHistory:
    def test_fighter_history_returns_fight_list(self, engine, client):
        """[19] GET /fighter/{name}/history returns fights from DB."""
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR IGNORE INTO fights (r_name, b_name, date, winner, method, weight_class)
                VALUES ('Fighter A', 'Fighter B', '2024-01-15', 'Fighter A', 'KO', 'Lightweight')
            """))

        resp = client.get("/fighter/Fighter A/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Fighter A"
        assert "fights" in body
        assert "count" in body
        assert body["count"] >= 1
        fight = body["fights"][0]
        assert "opponent" in fight
        assert "date" in fight
        assert fight["result"] in ("W", "L")
        assert "method" in fight

    def test_fighter_history_unknown_fighter_returns_404(self, client):
        """[19b] GET /fighter/{name}/history → 404 when no fights found."""
        resp = client.get("/fighter/Unknown Fighter XYZ/history")
        assert resp.status_code == 404

    def test_fighter_history_blue_corner_path(self, engine, client):
        """[22] Fighter appearing as b_name (blue corner) is found and opponent is r_name."""
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT OR IGNORE INTO fights (r_name, b_name, date, winner, method, weight_class)
                VALUES ('Fighter C', 'Fighter B', '2024-03-01', 'Fighter C', 'SUB', 'Featherweight')
            """))

        resp = client.get("/fighter/Fighter B/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Fighter B"
        assert body["count"] >= 1
        fight = body["fights"][0]
        assert fight["opponent"] == "Fighter C"
        assert fight["result"] == "L"  # Fighter B lost


# ── /generate-ai-analysis tests ───────────────────────────────────────────────

class TestGenerateAIAnalysis:
    _payload = {
        "fighter1": "Fighter A",
        "fighter2": "Fighter B",
        "winner": "Fighter A",
        "confidence": 0.65,
        "fighter1_stats": {
            "wins_total": 18, "losses_total": 3, "age": 30,
            "height": 180, "reach": 185, "SLpM_total": 4.2,
            "sig_str_acc_total": 0.48, "td_acc_total": 0.40,
        },
        "fighter2_stats": {
            "wins_total": 14, "losses_total": 4, "age": 28,
            "height": 178, "reach": 180, "SLpM_total": 3.8,
            "sig_str_acc_total": 0.44, "td_acc_total": 0.35,
        },
    }

    def test_generate_ai_analysis_returns_analysis(self, client):
        """[20] POST /generate-ai-analysis returns analysis dict via asyncio.to_thread."""
        with patch.object(
            app_module.ai_analyst, 'generate_fight_analysis',
            return_value={"key_factors": ["test"], "confidence_level": "HIGH"}
        ):
            resp = client.post("/generate-ai-analysis", json=self._payload)
        assert resp.status_code == 200
        body = resp.json()
        assert "analysis" in body
        assert body["analysis"]["confidence_level"] == "HIGH"

    def test_generate_ai_analysis_rate_limit_429_on_fourth_request(self, client):
        """[21] POST /generate-ai-analysis: 4th request in the same hour → 429."""
        # The limiter is in-memory at the app-module level and persists across
        # tests. Reset it so this test always starts from a clean counter.
        app_module.limiter._storage.reset()

        with patch.object(
            app_module.ai_analyst, 'generate_fight_analysis',
            return_value={"key_factors": [], "confidence_level": "LOW"}
        ):
            for _ in range(3):
                r = client.post("/generate-ai-analysis", json=self._payload)
                assert r.status_code == 200
            r4 = client.post("/generate-ai-analysis", json=self._payload)
        assert r4.status_code == 429


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
