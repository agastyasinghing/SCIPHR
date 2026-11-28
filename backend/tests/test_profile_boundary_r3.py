"""
FTR-01B1-R3 — identity isolation, enum-hardened validation, calculator-fallback classification.

Endpoint tests: real FastAPI app + real GoldenFeatureCalculator + disposable SQLite.
"""

import copy
import datetime as dt
import json
import logging
import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as app_module
from main import app
from db.models import Fighter, Fight
from golden_feature_calculator import GoldenFeatureCalculator
from fighter_profile import attribute_fights, inspect_legacy_raw_stats
from fighter_profile import service as service_mod
from fighter_profile.service import guard_extension, validate_extension, ExtensionValidationError
from tests.test_profile_api import COMPLETE
from tests.test_profile_review_corrections import _complete_extension

app.router.on_startup.clear()
app.router.on_shutdown.clear()
LOG = logging.getLogger("r3")


def _fighter(name, **kw):
    d = dict(COMPLETE)
    d.update(name=name, **kw)
    return d


def _fight(r, b, winner, day, method=None):
    return dict(r_name=r, b_name=b, date=dt.date(2024, 1, day), winner=winner, method=method,
                weight_class="Lightweight")


def _strict(resp):
    assert resp.status_code == 200, resp.text
    assert "NaN" not in resp.text and "Infinity" not in resp.text
    return json.loads(resp.text, parse_constant=lambda c: pytest.fail(f"non-standard constant {c}"))


def _sql(engine, stmt, **params):
    with engine.begin() as conn:                 # disposable in-memory SQLite only
        conn.execute(text(stmt), params)


@pytest.fixture
def real_api(engine):
    def make(fighters, fights=()):
        with Session(engine) as s:
            for d in fighters:
                s.add(Fighter(latest_features={"r_fighter_SlpM": 1.0}, **d))
            for f in fights:
                s.add(Fight(**f))
            s.commit()
        names = {d["name"] for d in fighters}
        predictor = MagicMock()
        predictor.search_fighter.side_effect = lambda n: n if n in names else None
        predictor.feature_calculator = GoldenFeatureCalculator(engine)      # REAL
        app_module.engine = engine
        app_module.predictor = predictor
        app_module.orchestrator = MagicMock()
        return TestClient(app, raise_server_exceptions=False)

    yield make
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None


# ═══ FIX 1 — identity collisions ═══════════════════════════════════════════
class TestIdentityCollision:
    FIGHTERS = ["Same Name", "Same  Name"]          # two distinct fighter records

    def _client(self, real_api, fights):
        return real_api([_fighter(n) for n in self.FIGHTERS], fights=fights)

    def test_A_each_fighter_gets_only_their_own_bout(self, real_api):
        c = self._client(real_api, [
            _fight("Same Name", "Opp One", "Same Name", 1),          # fighter 1 wins
            _fight("Opp Two", "Same  Name", "Opp Two", 2),           # fighter 2 loses
        ])
        h1 = _strict(c.get("/fighter/Same Name/history"))
        h2 = _strict(c.get("/fighter/Same  Name/history"))
        assert h1["count"] == 1 and h2["count"] == 1
        assert (h1["fights"][0]["opponent"], h1["fights"][0]["result"]) == ("Opp One", "W")
        assert (h2["fights"][0]["opponent"], h2["fights"][0]["result"]) == ("Opp Two", "L")
        assert h1["name_match"]["status"] == "collision_resolved"
        assert h1["name_match"]["excluded_other_identity_bouts"] == 1
        assert h1["name_match"]["ambiguous_identity"] is True
        assert h1["name_match"]["candidates"] == ["Same  Name", "Same Name"]
        for h in (h1, h2):
            assert h["name_match"]["coverage_verified"] is True
            assert h["result_counts"]["W"] + h["result_counts"]["L"] == 1

    def test_F_profile_coverage_agrees_with_history(self, real_api):
        c = self._client(real_api, [
            _fight("Same Name", "Opp One", "Same Name", 1),
            _fight("Opp Two", "Same  Name", "Opp Two", 2),
            _fight("Same  Name", "Opp Three", "Same  Name", 3),
        ])
        for n, expected in (("Same Name", 1), ("Same  Name", 2)):
            cov = _strict(c.get(f"/fighter/{n}"))["data_quality"]["coverage"]
            h = _strict(c.get(f"/fighter/{n}/history"))
            assert cov["ufc_fights_in_dataset"] == h["count"] == expected
            assert cov["coverage_verified"] is True and cov["identity_status"] == "collision_resolved"

    def test_collision_fighters_who_fought_each_other(self, real_api):
        c = self._client(real_api, [_fight("Same Name", "Same  Name", "Same  Name", 1)])
        h1 = _strict(c.get("/fighter/Same Name/history"))["fights"][0]
        h2 = _strict(c.get("/fighter/Same  Name/history"))["fights"][0]
        assert (h1["result"], h1["opponent"]) == ("L", "Same  Name")
        assert (h2["result"], h2["opponent"]) == ("W", "Same Name")

    def test_G_results_exact_in_collision_and_variant_winner_is_unknown(self, real_api):
        c = self._client(real_api, [
            _fight("Same Name", "A", "Draw", 1), _fight("Same Name", "B", "No Contest", 2),
            _fight("Same Name", "C", None, 3), _fight("Same Name", "D", "SAME NAME", 4),
            _fight("E", "Same Name", "E", 5),
        ])
        by = {f["date"]: f["result"] for f in _strict(c.get("/fighter/Same Name/history"))["fights"]}
        assert by == {"2024-01-01": "D", "2024-01-02": "NC", "2024-01-03": "UNKNOWN",
                      "2024-01-04": "UNKNOWN", "2024-01-05": "L"}

    def test_D_ambiguous_candidate_without_safe_match_is_withheld_not_zero(self, real_api):
        c = self._client(real_api, [_fight("SAME NAME", "Opp", "SAME NAME", 1)])
        for n in self.FIGHTERS:
            h = _strict(c.get(f"/fighter/{n}/history"))          # 200, not a 404 "no history"
            assert h["count"] == 0 and h["fights"] == []
            assert h["name_match"]["status"] == "ambiguous_unattributable"
            assert h["name_match"]["withheld_ambiguous_bouts"] == 1
            assert h["name_match"]["coverage_verified"] is False
            assert h["history_scope"]["coverage_verified"] is False
            assert h["methods_available_fraction"] is None
            b = _strict(c.get(f"/fighter/{n}"))
            cov = b["data_quality"]["coverage"]
            assert cov["ufc_fights_in_dataset"] is None            # never a verified 0
            assert cov["coverage_verified"] is False and cov["withheld_ambiguous_bouts"] == 1
            assert cov["identity_status"] == "ambiguous_unattributable"
            assert b["extension_status"]["available"] is True      # honest metadata passes validation

    def test_partial_attribution_reports_incomplete_coverage(self, real_api):
        c = self._client(real_api, [_fight("Same Name", "Opp", "Same Name", 1),
                                    _fight("SAME NAME", "Opp2", "SAME NAME", 2)])
        h = _strict(c.get("/fighter/Same Name/history"))
        assert h["count"] == 1 and h["name_match"]["status"] == "collision_partial"
        assert h["name_match"]["withheld_ambiguous_bouts"] == 1
        assert h["name_match"]["coverage_verified"] is False
        cov = _strict(c.get("/fighter/Same Name"))["data_quality"]["coverage"]
        assert cov["ufc_fights_in_dataset"] == 1 and cov["coverage_verified"] is False

    def test_requested_name_not_an_exact_candidate_attributes_nothing(self, engine, real_api):
        self._client(real_api, [_fight("Same Name", "Opp", "Same Name", 1)])
        with engine.connect() as conn:
            att = attribute_fights(conn, "same name")
        assert att.rows == [] and att.status == "ambiguous_unattributable"
        assert att.requested_exact is False and att.coverage_verified is False

    def test_B_unique_fighter_with_extra_spaces_still_matches(self, real_api):
        c = real_api([_fighter("Solo Fighter")],
                     [_fight("  Solo Fighter  ", "Opp", "solo fighter", 1),
                      _fight("Opp", "SOLO   FIGHTER", "Opp", 2)])
        h = _strict(c.get("/fighter/Solo Fighter/history"))
        assert h["count"] == 2 and h["name_match"]["status"] == "unique"
        assert [f["result"] for f in h["fights"]] == ["L", "W"]
        assert h["name_match"]["coverage_verified"] is True

    def test_C_unique_fighter_with_case_variation(self, real_api):
        c = real_api([_fighter("Mixed Case")], [_fight("MIXED CASE", "Opp", "MIXED CASE", 1)])
        h = _strict(c.get("/fighter/Mixed Case/history"))
        assert h["count"] == 1 and h["fights"][0]["result"] == "W"
        assert h["fights"][0]["opponent"] == "Opp"

    def test_E_normal_names_unchanged(self, real_api):
        c = real_api([_fighter("Plain One"), _fighter("Plain Two")], [_fight("Plain One", "Plain Two", "Plain One", 1)])
        a = _strict(c.get("/fighter/Plain One/history"))
        b = _strict(c.get("/fighter/Plain Two/history"))
        assert (a["fights"][0]["result"], b["fights"][0]["result"]) == ("W", "L")
        assert a["name_match"]["status"] == "unique" and a["name_match"]["candidates"] == []
        cov = _strict(c.get("/fighter/Plain One"))["data_quality"]["coverage"]
        assert cov["ufc_fights_in_dataset"] == 1 and cov["coverage_verified"] is True
        assert cov["identity_status"] == "unique"

    def test_H_no_substring_or_fuzzy_attribution(self, engine, real_api):
        real_api([_fighter("Same Name"), _fighter("Same  Name")], [_fight("Same Name", "Opp", "Same Name", 1)])
        with engine.connect() as conn:
            for probe in ("Same", "Name", "Same Nam", "Sam Name", "Same Name Jr"):
                att = attribute_fights(conn, probe)
                assert att.rows == [] and att.withheld_ambiguous == 0, probe

    def test_attribution_issues_only_select(self, engine, real_api):
        from sqlalchemy import event
        c = self._client(real_api, [_fight("Same Name", "Opp", "Same Name", 1)])
        seen = []

        @event.listens_for(engine, "before_cursor_execute")
        def cap(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)
        c.get("/fighter/Same Name/history")
        c.get("/fighter/Same Name")
        assert seen and all(s_.lstrip().upper().startswith("SELECT") for s_ in seen)

    def test_validator_rejects_verified_null_count(self):
        ext = copy.deepcopy(_complete_extension())
        ext["data_quality"]["coverage"]["ufc_fights_in_dataset"] = None
        ext["data_quality"]["coverage"]["coverage_verified"] = True
        with pytest.raises(ExtensionValidationError):
            validate_extension(ext)
        ext["data_quality"]["coverage"]["coverage_verified"] = False
        validate_extension(ext)


# ═══ FIX 2 — enum type-checking and safe logging ═══════════════════════════
UNHASHABLE_AND_BAD = [[], {}, None, 5, 1.5, True, ["a"], {"x": 1}, "not-an-enum", ""]


def _set(path, value):
    def fn(e):
        o = e
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = value
    return fn


ENUM_TARGETS = {
    "field.status": ["data_quality", "fields", "slpm", "status"],
    "field.basis": ["data_quality", "fields", "slpm", "basis"],
    "block.status": ["data_quality", "core_stat_block", "status"],
    "score.status": ["scores", "composite", "status"],
}


class TestEnumValidation:
    @pytest.mark.parametrize("target", sorted(ENUM_TARGETS))
    @pytest.mark.parametrize("bad", UNHASHABLE_AND_BAD, ids=repr)
    def test_validator_rejects_with_validation_error_never_typeerror(self, target, bad):
        ext = copy.deepcopy(_complete_extension())
        _set(ENUM_TARGETS[target], bad)(ext)
        with pytest.raises(ExtensionValidationError):
            validate_extension(ext)

    @pytest.mark.parametrize("target", sorted(ENUM_TARGETS))
    @pytest.mark.parametrize("bad", UNHASHABLE_AND_BAD, ids=repr)
    def test_guard_degrades_to_invalid_shape(self, target, bad):
        ext = copy.deepcopy(_complete_extension())
        _set(ENUM_TARGETS[target], bad)(ext)
        out = guard_extension(lambda e, n: ext, object(), "A", LOG)
        assert out == {"data_quality": None, "scores": None,
                       "extension_status": {"available": False, "reason": "INVALID_SHAPE"}}

    @pytest.mark.parametrize("target", sorted(ENUM_TARGETS))
    @pytest.mark.parametrize("bad", [[], {}, None, 5, "bogus"], ids=repr)
    def test_endpoint_returns_200_with_explicit_degradation(self, real_api, monkeypatch, target, bad):
        c = real_api([_fighter("Enum Case")])
        ext = copy.deepcopy(_complete_extension())
        _set(ENUM_TARGETS[target], bad)(ext)
        monkeypatch.setattr(app_module, "build_profile_extension", lambda e, n: ext)
        b = _strict(c.get("/fighter/Enum Case"))                 # HTTP 200, not 500
        assert b["extension_status"] == {"available": False, "reason": "INVALID_SHAPE"}
        assert b["data_quality"] is None and b["scores"] is None
        assert "stats" in b and "intelligence" in b and "legacy_integrity" in b

    def test_unexpected_exception_inside_validation_is_contained(self, monkeypatch, caplog):
        def explode(ext):
            raise TypeError("SECRET_MARKER inside validator")
        monkeypatch.setattr(service_mod, "validate_extension", explode)
        with caplog.at_level(logging.WARNING):
            out = guard_extension(lambda e, n: _complete_extension(), object(), "Fighter X", LOG)
        assert out["extension_status"]["reason"] == "INVALID_SHAPE"
        assert "VALIDATION_FAULT" in caplog.text and "TypeError" in caplog.text
        assert "SECRET_MARKER" not in caplog.text

    def test_deeply_nested_payload_is_contained(self):
        ext = copy.deepcopy(_complete_extension())
        node = ext["data_quality"]["legacy_compat"]
        for _ in range(3000):
            node["n"] = {}
            node = node["n"]
        out = guard_extension(lambda e, n: ext, object(), "A", LOG)
        assert out["extension_status"]["reason"] == "INVALID_SHAPE"

    def test_valid_payload_still_succeeds_and_is_returned_unchanged(self):
        ext = _complete_extension()
        out = guard_extension(lambda e, n: ext, object(), "A", LOG)
        assert out["extension_status"] == {"available": True, "reason": None}
        assert out["data_quality"] is ext["data_quality"] and out["scores"] is ext["scores"]

    def test_builder_failures_still_map_to_error_and_missing_to_not_found(self):
        def boom(e, n):
            raise ValueError("builder")
        assert guard_extension(boom, object(), "A", LOG)["extension_status"]["reason"] == "ERROR"
        assert guard_extension(lambda e, n: None, object(), "A", LOG)["extension_status"]["reason"] == "NOT_FOUND"


class TestSafeValidationLogging:
    MARKER = "SECRET_MARKER_9f3a"

    def _log_for(self, mutate, caplog):
        ext = copy.deepcopy(_complete_extension())
        mutate(ext)
        with caplog.at_level(logging.WARNING):
            out = guard_extension(lambda e, n: ext, object(), "Fighter Y", LOG)
        assert out["extension_status"]["reason"] == "INVALID_SHAPE"
        return caplog.text

    def test_payload_key_never_appears_in_nonfinite_log(self, caplog):
        """The reviewer's synthetic marker: an arbitrary nested key holding NaN."""
        txt = self._log_for(lambda e: e["data_quality"]["legacy_compat"].__setitem__(self.MARKER, float("nan")), caplog)
        assert self.MARKER not in txt
        assert "NON_FINITE_NUMBER" in txt and "Fighter Y" in txt

    def test_payload_values_and_keys_never_logged(self, caplog):
        def mutate(e):
            e["data_quality"]["fields"]["slpm"]["status"] = self.MARKER
            e["data_quality"]["fields"][self.MARKER] = {"value": self.MARKER}
        txt = self._log_for(mutate, caplog)
        assert self.MARKER not in txt
        assert "FIELD_STATUS_INVALID" in txt and "slpm" in txt        # fixed code + allowlisted field id

    def test_marker_in_score_and_coverage(self, caplog):
        def mutate(e):
            e["scores"]["composite"]["reason"] = 5
            e["scores"]["composite"]["available"] = self.MARKER
        assert self.MARKER not in self._log_for(mutate, caplog)

    def test_builder_exception_message_not_logged(self, caplog):
        def boom(e, n):
            raise RuntimeError(f"postgresql://u:{self.MARKER}@h/db")
        with caplog.at_level(logging.WARNING):
            guard_extension(boom, object(), "Fighter Z", LOG)
        assert "RuntimeError" in caplog.text and self.MARKER not in caplog.text
        assert "postgresql://" not in caplog.text


# ═══ FIX 3 — calculator fallback classification ════════════════════════════
class TestFallbackClassification:
    def test_real_malformed_stored_slpm_recovers(self, engine, real_api):
        c = real_api([_fighter("Junk A")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='Junk A'")
        b = _strict(c.get("/fighter/Junk A"))
        assert b["legacy_integrity"]["raw_input_corruption"][0]["field"] == "fighter_SlpM"

    def test_inspection_reports_coercion_failures_only_for_unconvertible_values(self, engine, real_api):
        real_api([_fighter("I1"), _fighter("I2"), _fighter("I3")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='I1'")
        _sql(engine, "UPDATE fighters SET slpm=:v WHERE name='I2'", v=float("inf"))
        r1 = inspect_legacy_raw_stats(engine, "I1")
        r2 = inspect_legacy_raw_stats(engine, "I2")
        r3 = inspect_legacy_raw_stats(engine, "I3")
        assert r1["coercion_failures"] == ["fighter_SlpM"] and r1["malformed"] == ["fighter_SlpM"]
        assert r2["coercion_failures"] == [] and r2["malformed"] == ["fighter_SlpM"]   # inf: float() works
        assert r3["coercion_failures"] == [] and r3["malformed"] == []
        assert inspect_legacy_raw_stats(engine, "Nobody")["found"] is False

    @pytest.mark.parametrize("exc", [ValueError("unrelated bug"), TypeError("unrelated bug")])
    def test_valid_row_plus_injected_error_propagates(self, real_api, exc):
        c = real_api([_fighter("Valid P")])
        app_module.predictor.feature_calculator = MagicMock()
        app_module.predictor.feature_calculator.get_latest_fighter_stats.side_effect = exc
        r = c.get("/fighter/Valid P")
        assert r.status_code == 500                                   # NOT a 200 with corrupted=false
        assert "legacy_integrity" not in r.text

    def test_nonfinite_but_convertible_value_does_not_justify_recovery(self, engine, real_api):
        c = real_api([_fighter("Inf Q")])
        _sql(engine, "UPDATE fighters SET slpm=:v WHERE name='Inf Q'", v=float("inf"))
        app_module.predictor.feature_calculator = MagicMock()
        app_module.predictor.feature_calculator.get_latest_fighter_stats.side_effect = ValueError("bug")
        assert c.get("/fighter/Inf Q").status_code == 500

    def test_required_db_read_failure_propagates(self, engine, real_api, monkeypatch):
        c = real_api([_fighter("Junk R")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='Junk R'")

        def down(*a, **k):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        monkeypatch.setattr(app_module, "inspect_legacy_raw_stats", down)
        r = c.get("/fighter/Junk R")
        assert r.status_code == 500 and "stats" not in r.text

    def test_missing_row_with_calculator_error_propagates(self, real_api):
        c = real_api([_fighter("Ghost S")])
        # R4: identity is resolved against the fighters table first, so a name with no row is a
        # 404 before the calculator runs; a resolved fighter with no unconvertible value and a
        # calculator error is still a real bug (500).
        app_module.predictor.feature_calculator = MagicMock()
        app_module.predictor.feature_calculator.get_latest_fighter_stats.side_effect = ValueError("bug")
        assert c.get("/fighter/Not In Table").status_code == 404
        assert c.get("/fighter/Ghost S").status_code == 500

    def test_valid_profile_legacy_payload_unchanged(self, real_api):
        c = real_api([_fighter("Valid T")])
        b = _strict(c.get("/fighter/Valid T"))
        assert b["intelligence"] == {"style": "STRIKER", "is_active": True, "aura_score": 75.7,
                                     "composite_score": 100.0, "chaos_contribution": 51.0,
                                     "mirage_meter": 0.0, "scores_source": "heuristic"}
        assert b["stats"]["SLpM_total"] == 4.2 and b["stats"]["wins_total"] == 18.0
        assert b["legacy_integrity"]["corrupted"] is False
        assert b["extension_status"] == {"available": True, "reason": None}
        assert b["scores"]["mirage"]["reason"] == "UNVALIDATED_HEURISTIC"
