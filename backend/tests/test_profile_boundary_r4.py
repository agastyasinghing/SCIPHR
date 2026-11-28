"""
FTR-01B1-R4 — fighter identity is resolved BEFORE profile/history lookup.

Real FastAPI routes + real GoldenFeatureCalculator + disposable SQLite.  The predictor's
REAL ``search_fighter`` (case-insensitive first match) is used - it is not mocked - so a
first-match regression is caught.
"""

import datetime as dt
import json
import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import main as app_module
from main import app
from db.models import Fighter, Fight
from golden_feature_calculator import GoldenFeatureCalculator
from predictor_golden import UFCFightPredictorGolden
from fighter_profile import resolve_fighter_identity, AmbiguousFighterIdentity
from tests.test_profile_api import COMPLETE

app.router.on_startup.clear()
app.router.on_shutdown.clear()


def _fighter(name, **kw):
    d = dict(COMPLETE)
    d.update(name=name, **kw)
    return d


def _fight(r, b, winner, day):
    return dict(r_name=r, b_name=b, date=dt.date(2024, 1, day), winner=winner, method=None,
                weight_class="Lightweight")


def _ok(resp):
    assert resp.status_code == 200, resp.text
    return json.loads(resp.text)


@pytest.fixture
def api(engine):
    def make(fighters, fights=()):
        with Session(engine) as s:
            for d in fighters:
                s.add(Fighter(latest_features={"r_fighter_SlpM": 1.0}, **d))
            for f in fights:
                s.add(Fight(**f))
            s.commit()
        # REAL search_fighter on a real list built the same way the real predictor builds it
        predictor = object.__new__(UFCFightPredictorGolden)
        predictor.available_fighters = [d["name"] for d in sorted(fighters, key=lambda d: d["name"])]
        predictor.feature_calculator = GoldenFeatureCalculator(engine)
        app_module.engine = engine
        app_module.predictor = predictor
        app_module.orchestrator = MagicMock()
        return TestClient(app, raise_server_exceptions=False)

    yield make
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None


def _case_twins(api):
    return api(
        [_fighter("Case Twin", wins=10, losses=1, slpm=3.0, aura_score=11.0, composite_score=21.0,
                  chaos_contribution=31.0, mirage_meter=41.0, style="STRIKER"),
         _fighter("CASE TWIN", wins=2, losses=9, slpm=5.5, aura_score=88.0, composite_score=77.0,
                  chaos_contribution=66.0, mirage_meter=55.0, style="GRAPPLER")],
        [_fight("Case Twin", "Opp Lower", "Case Twin", 1),
         _fight("Case Twin", "Opp Lower 2", "Opp Lower 2", 2),
         _fight("CASE TWIN", "Opp Upper", "Opp Upper", 3)],
    )


# ═══ FIXTURE A — case-only collision ═══════════════════════════════════════
class TestCaseOnlyCollision:
    def test_real_search_fighter_is_first_match(self, api):
        """Guard: the bug's premise holds - the real lookup cannot tell the twins apart."""
        _case_twins(api)
        s = app_module.predictor.search_fighter
        assert s("Case Twin") == s("CASE TWIN")

    @pytest.mark.parametrize("name,wins,slpm,aura,style,opps", [
        ("Case Twin", 10.0, 3.0, 11.0, "STRIKER", {"Opp Lower", "Opp Lower 2"}),
        ("CASE TWIN", 2.0, 5.5, 88.0, "GRAPPLER", {"Opp Upper"}),
    ])
    def test_exact_request_selects_exact_fighter_everywhere(self, api, name, wins, slpm, aura, style, opps):
        c = _case_twins(api)
        b = _ok(c.get(f"/fighter/{name.replace(' ', '%20')}"))
        assert b["name"] == name
        assert b["stats"]["wins_total"] == wins and b["stats"]["SLpM_total"] == slpm
        assert b["intelligence"]["aura_score"] == aura
        assert b["intelligence"]["style"] == style and b["intelligence"]["scores_source"] == "computed"
        h = _ok(c.get(f"/fighter/{name.replace(' ', '%20')}/history"))
        assert h["name"] == name
        assert {f["opponent"] for f in h["fights"]} == opps
        cov = b["data_quality"]["coverage"]
        assert cov["ufc_fights_in_dataset"] == h["count"] == len(opps)
        assert cov["coverage_verified"] is True and h["name_match"]["coverage_verified"] is True

    def test_no_cross_fighter_values(self, api):
        c = _case_twins(api)
        lower = _ok(c.get("/fighter/Case%20Twin"))
        upper = _ok(c.get("/fighter/CASE%20TWIN"))
        blob_lower, blob_upper = json.dumps(lower), json.dumps(upper)
        for forbidden in ("88.0", "77.0", "Opp Upper", "CASE TWIN"):
            assert forbidden not in blob_lower.replace("collision_resolved", "")
        for forbidden in ("Opp Lower", "\"Case Twin\""):
            assert forbidden not in blob_upper
        assert lower["intelligence"]["composite_score"] == 21.0
        assert upper["intelligence"]["composite_score"] == 77.0
        assert lower["intelligence"]["chaos_contribution"] == 31.0
        assert upper["intelligence"]["mirage_meter"] == 55.0

    def test_results_per_fighter(self, api):
        c = _case_twins(api)
        h = _ok(c.get("/fighter/Case%20Twin/history"))
        assert {f["opponent"]: f["result"] for f in h["fights"]} == {"Opp Lower": "W", "Opp Lower 2": "L"}
        h = _ok(c.get("/fighter/CASE%20TWIN/history"))
        assert {f["opponent"]: f["result"] for f in h["fights"]} == {"Opp Upper": "L"}


# ═══ FIXTURE B — non-exact case collision ══════════════════════════════════
class TestNonExactCaseCollision:
    def test_profile_and_history_return_409(self, api):
        c = _case_twins(api)
        for path in ("/fighter/case%20twin", "/fighter/case%20twin/history"):
            r = c.get(path)
            assert r.status_code == 409, r.text
            assert r.json()["detail"] == {"code": "AMBIGUOUS_FIGHTER_IDENTITY",
                                          "candidates": ["CASE TWIN", "Case Twin"]}
            assert "stats" not in r.text and "fights" not in r.text      # no partial payload


# ═══ FIXTURE C — spacing collision ═════════════════════════════════════════
class TestSpacingCollision:
    def _c(self, api):
        return api([_fighter("Same Name", wins=7), _fighter("Same  Name", wins=3)],
                   [_fight("Same Name", "Opp A", "Same Name", 1), _fight("Opp B", "Same  Name", "Opp B", 2)])

    def test_exact_requests_select_their_fighter(self, api):
        c = self._c(api)
        assert _ok(c.get("/fighter/Same Name"))["stats"]["wins_total"] == 7.0
        assert _ok(c.get("/fighter/Same  Name"))["stats"]["wins_total"] == 3.0
        assert _ok(c.get("/fighter/Same Name"))["name"] == "Same Name"
        assert _ok(c.get("/fighter/Same  Name"))["name"] == "Same  Name"
        assert [f["opponent"] for f in _ok(c.get("/fighter/Same  Name/history"))["fights"]] == ["Opp B"]

    @pytest.mark.parametrize("path", ["/fighter/same%20name", "/fighter/same%20name/history",
                                      "/fighter/SAME%20NAME", "/fighter/Same%20%20%20Name"])
    def test_non_exact_request_is_409_with_stored_candidates(self, api, path):
        r = self._c(api).get(path)
        assert r.status_code == 409
        assert r.json()["detail"] == {"code": "AMBIGUOUS_FIGHTER_IDENTITY",
                                      "candidates": ["Same  Name", "Same Name"]}


# ═══ FIXTURE D — unique normalised name ════════════════════════════════════
class TestUniqueNormalized:
    def _c(self, api):
        return api([_fighter("Review Red")], [_fight("Review Red", "Opp", "Review Red", 1)])

    @pytest.mark.parametrize("raw", ["review%20red", "REVIEW%20RED", "%20%20Review%20%20Red%20%20", "Review%20%20Red"])
    def test_tolerant_lookup_resolves_stored_name(self, api, raw):
        c = self._c(api)
        b = _ok(c.get(f"/fighter/{raw}"))
        h = _ok(c.get(f"/fighter/{raw}/history"))
        assert b["name"] == h["name"] == "Review Red"
        assert b["data_quality"]["coverage"]["ufc_fights_in_dataset"] == h["count"] == 1

    def test_unknown_is_404(self, api):
        c = self._c(api)
        assert c.get("/fighter/Nobody%20Here").status_code == 404
        assert c.get("/fighter/Nobody%20Here/history").status_code == 404


# ═══ FIXTURE E — fuzzy ═════════════════════════════════════════════════════
class TestFuzzy:
    def test_unambiguous_fuzzy_still_works(self, api):
        c = api([_fighter("Jonathan Fuzzy"), _fighter("Other Person")])
        assert _ok(c.get("/fighter/Jonathan%20Fuzzy%20Jr"))["name"] == "Jonathan Fuzzy"   # stored name inside request
        assert _ok(c.get("/fighter/Fuzzy"))["name"] == "Jonathan Fuzzy"                    # partial

    def test_fuzzy_cannot_bypass_a_collision(self, engine):
        with Session(engine) as s:
            for n in ("Dup One", "DUP ONE"):
                s.add(Fighter(latest_features={}, **_fighter(n)))
            s.commit()
        with engine.connect() as conn:
            # a fuzzy search that (wrongly) returns one of the colliding stored names
            with pytest.raises(AmbiguousFighterIdentity) as e:
                resolve_fighter_identity(conn, "dup", lambda n: "Dup One")
        assert e.value.candidates == ["DUP ONE", "Dup One"]

    def test_fuzzy_result_not_in_db_is_unresolved(self, engine):
        with engine.connect() as conn:
            assert resolve_fighter_identity(conn, "x", lambda n: "Phantom") is None


# ═══ FIXTURE F — failure behaviour ═════════════════════════════════════════
class TestFailure:
    def test_db_failure_propagates_not_first_match(self, api):
        c = _case_twins(api)
        broken = MagicMock()
        broken.connect.side_effect = OperationalError("SELECT", {}, Exception("db down"))
        app_module.engine = broken
        for path in ("/fighter/case%20twin", "/fighter/Case%20Twin", "/fighter/case%20twin/history"):
            r = c.get(path)
            assert r.status_code == 500
            assert "CASE TWIN" not in r.text and "Case Twin" not in r.text

    def test_status_codes(self, api):
        c = _case_twins(api)
        assert c.get("/fighter/Unknown%20Person").status_code == 404
        assert c.get("/fighter/case%20twin").status_code == 409
        assert c.get("/fighter/Case%20Twin").status_code == 200


# ═══ FIXTURE G — legacy compatibility ══════════════════════════════════════
class TestLegacyCompat:
    def test_unambiguous_response_unchanged(self, api):
        c = api([_fighter("Valid T")])
        b = _ok(c.get("/fighter/Valid T"))
        assert b["intelligence"] == {"style": "STRIKER", "is_active": True, "aura_score": 75.7,
                                     "composite_score": 100.0, "chaos_contribution": 51.0,
                                     "mirage_meter": 0.0, "scores_source": "heuristic"}
        assert b["stats"]["SLpM_total"] == 4.2 and b["stats"]["wins_total"] == 18.0
        assert b["legacy_integrity"]["corrupted"] is False
        assert set(b) == {"name", "data_quality", "scores", "extension_status", "legacy_integrity",
                          "stats", "intelligence"}


# ═══ Stored-score query is exact and SELECT-only ═══════════════════════════
class TestStoredScoreIsolation:
    def test_stored_score_query_is_exact_not_lower(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "main.py"), encoding="utf-8").read()
        assert "LOWER(name) = LOWER(:name)" not in src

    def test_resolver_is_select_only(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "fighter_profile", "identity.py"),
                   encoding="utf-8").read().upper()
        for word in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER "):
            assert word not in src.replace("SELECT-ONLY", "")


# ═══ R5 — fail closed when the application engine is missing ═══════════════
class TestMissingEngineFailsClosed:
    PATHS = ("/fighter/Case%20Twin", "/fighter/Case%20Twin/history",
             "/fighter/case%20twin", "/fighter/CASE%20TWIN")

    def test_engine_none_is_500_with_no_fighter_data(self, api, engine):
        c = _case_twins(api)
        # predictor and its calculator connection stay alive; only main.engine is missing
        assert app_module.predictor.feature_calculator.engine is engine
        app_module.engine = None
        for path in self.PATHS:
            r = c.get(path)
            assert r.status_code == 500, (path, r.text)
            assert r.json() == {"detail": "Database not initialized"}
            for leak in ("CASE TWIN", "Case Twin", "wins_total", "fights"):
                assert leak not in r.text

    def test_resolution_is_restored_with_engine(self, api, engine):
        c = _case_twins(api)
        app_module.engine = None
        assert c.get("/fighter/Case%20Twin").status_code == 500
        app_module.engine = engine
        lower, upper = _ok(c.get("/fighter/Case%20Twin")), _ok(c.get("/fighter/CASE%20TWIN"))
        assert (lower["name"], upper["name"]) == ("Case Twin", "CASE TWIN")
        assert lower["intelligence"]["aura_score"] == 11.0 and upper["intelligence"]["aura_score"] == 88.0
        assert c.get("/fighter/case%20twin").status_code == 409
        assert c.get("/fighter/case%20twin/history").status_code == 409

    def test_unique_fighter_still_resolves(self, api):
        c = api([_fighter("Review Red")])
        assert _ok(c.get("/fighter/review%20red"))["name"] == "Review Red"
