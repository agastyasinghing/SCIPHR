"""
FTR-01B1-R2 — profile boundary and history-lookup regressions.

Endpoint tests use the REAL FastAPI app, the REAL GoldenFeatureCalculator and a
disposable SQLite database (malformed values are injected with raw SQL, the way
SQLite's loose typing allows).  Only the fuzzy name search is mocked.
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
from fighter_profile.service import (
    ExtensionValidationError, guard_extension, validate_extension, fetch_fight_rows,
)
from tests.test_profile_api import COMPLETE
from tests.test_profile_review_corrections import _complete_extension

app.router.on_startup.clear()
app.router.on_shutdown.clear()

LOG = logging.getLogger("r2")


def _fighter(name, **kw):
    d = dict(COMPLETE)
    d.update(name=name, **kw)
    return d


def _strict(resp):
    assert resp.status_code == 200, resp.text
    assert "NaN" not in resp.text and "Infinity" not in resp.text
    return json.loads(resp.text, parse_constant=lambda c: pytest.fail(f"non-standard constant {c}"))


@pytest.fixture
def real_api(engine):
    """Factory: real calculator + disposable SQLite.  real_api(fighters, fights=()) -> client."""

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


def _sql(engine, stmt, **params):
    with engine.begin() as conn:                 # disposable in-memory SQLite only
        conn.execute(text(stmt), params)


# ═══ FIX 1 — malformed persisted numerics ══════════════════════════════════
class TestMalformedPersistedInputs:
    def test_precondition_shared_calculator_really_raises(self, engine, real_api):
        real_api([_fighter("Junk A")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='Junk A'")
        with pytest.raises(ValueError):
            GoldenFeatureCalculator(engine).get_latest_fighter_stats("Junk A")

    def test_failure_a_junk_slpm_returns_200(self, engine, real_api):
        c = real_api([_fighter("Junk A")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='Junk A'")
        b = _strict(c.get("/fighter/Junk A"))
        assert b["stats"]["SLpM_total"] == 0.0                              # legacy placeholder
        li = b["legacy_integrity"]
        assert li["corrupted"] is True
        assert li["raw_input_corruption"] == [
            {"field": "fighter_SlpM", "reason": "invalid_value", "legacy_placeholder": 0.0}]
        # derived legacy scores that read slpm are withheld; others untouched
        assert b["intelligence"]["aura_score"] is None
        assert b["intelligence"]["chaos_contribution"] is None
        assert b["intelligence"]["composite_score"] == 100.0                # legacy value, unaffected input
        assert {a["score"] for a in li["derived_scores_affected"]} == {"aura_score", "chaos_contribution"}
        # new layer: invalid value never feeds scores
        assert b["data_quality"]["fields"]["slpm"]["basis"] == "invalid_value"
        assert b["scores"]["aura"]["available"] is False
        assert b["scores"]["chaos_contribution"]["available"] is False

    @pytest.mark.parametrize("col,val", [("aura_score", "junk"), ("composite_score", "x"),
                                         ("chaos_contribution", float("inf")),
                                         ("mirage_meter", float("-inf")), ("aura_score", 150.0),
                                         ("aura_score", -5.0)])
    def test_failure_b_corrupted_stored_scores_return_200(self, engine, real_api, col, val):
        c = real_api([_fighter("Junk B")])
        _sql(engine, f"UPDATE fighters SET {col}=:v WHERE name='Junk B'", v=val)
        b = _strict(c.get("/fighter/Junk B"))
        li = b["legacy_integrity"]
        assert [e["field"] for e in li["stored_score_corruption"]] == [col]
        assert li["stored_score_corruption"][0]["reason"] in ("invalid_value", "invalid_range")
        assert li["raw_input_corruption"] == [] and li["derived_scores_affected"] == []
        assert b["intelligence"]["scores_source"] == "heuristic"             # never "computed"
        for k in ("aura_score", "composite_score", "chaos_contribution", "mirage_meter"):
            assert isinstance(b["intelligence"][k], float)                    # fell back to heuristics

    def test_corrupted_stored_scores_are_ignored_not_trusted(self, engine, real_api):
        c = real_api([_fighter("Junk C"), _fighter("Clean C")])
        _sql(engine, "UPDATE fighters SET aura_score='junk', composite_score=12.5 WHERE name='Junk C'")
        a = _strict(c.get("/fighter/Junk C"))["intelligence"]
        ref = _strict(c.get("/fighter/Clean C"))["intelligence"]
        assert a["composite_score"] == ref["composite_score"] != 12.5         # valid stored value also ignored
        assert a["aura_score"] == ref["aura_score"]

    def test_valid_stored_scores_preserved_exactly(self, engine, real_api):
        c = real_api([_fighter("Stored D")])
        _sql(engine, "UPDATE fighters SET aura_score=77.5, composite_score=61.25, "
                     "chaos_contribution=40, mirage_meter=0 WHERE name='Stored D'")
        b = _strict(c.get("/fighter/Stored D"))
        assert b["intelligence"]["aura_score"] == 77.5
        assert b["intelligence"]["composite_score"] == 61.25
        assert b["intelligence"]["chaos_contribution"] == 40.0
        assert b["intelligence"]["mirage_meter"] == 0.0
        assert b["intelligence"]["scores_source"] == "computed"
        assert b["legacy_integrity"]["corrupted"] is False

    def test_valid_fixture_legacy_response_identical(self, real_api):
        """Real calculator, valid data: exact legacy values and types (pre-R2 behaviour)."""
        c = real_api([_fighter("Valid E")])
        b = _strict(c.get("/fighter/Valid E"))
        i, st = b["intelligence"], b["stats"]
        assert i == {"style": "STRIKER", "is_active": True, "aura_score": 75.7, "composite_score": 100.0,
                     "chaos_contribution": 51.0, "mirage_meter": 0.0, "scores_source": "heuristic"}
        assert st["wins_total"] == 18.0 and st["losses_total"] == 3.0 and st["draw"] == 0.0
        assert st["SLpM_total"] == 4.2 and st["sig_str_acc_total"] == pytest.approx(48.0)
        assert st["sig_str_def_total"] == pytest.approx(58.0) and st["total_knockdowns"] == 0.0
        assert all(isinstance(v, float) for k, v in st.items() if k != "weight_class")
        assert b["legacy_integrity"] == {
            "schema": "legacy_integrity_v1", "corrupted": False, "raw_input_corruption": [],
            "stored_score_corruption": [], "derived_scores_affected": [],
            "note": b["legacy_integrity"]["note"]}

    def test_database_failure_is_not_replaced_by_fabricated_data(self, engine, real_api, monkeypatch):
        c = real_api([_fighter("Junk F")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='Junk F'")

        def down(*a, **k):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        monkeypatch.setattr(app_module, "read_legacy_raw_stats", down)
        r = c.get("/fighter/Junk F")
        assert r.status_code == 500 and "stats" not in r.text

    def test_unrelated_programming_errors_are_not_swallowed(self, real_api):
        c = real_api([_fighter("Prog G")])
        app_module.predictor.feature_calculator = MagicMock()
        app_module.predictor.feature_calculator.get_latest_fighter_stats.side_effect = RuntimeError("bug")
        assert c.get("/fighter/Prog G").status_code == 500


# ═══ FIX 2 — corruption metadata ═══════════════════════════════════════════
class TestCorruptionMetadata:
    def test_negative_wins_withholds_derived_scores_and_reports_range(self, engine, real_api):
        c = real_api([_fighter("Neg Wins")])
        _sql(engine, "UPDATE fighters SET wins=-1 WHERE name='Neg Wins'")
        b = _strict(c.get("/fighter/Neg Wins"))
        li = b["legacy_integrity"]
        assert li["raw_input_corruption"][0] == {
            "field": "fighter_w", "reason": "invalid_range", "legacy_placeholder": 0.0}
        i = b["intelligence"]
        assert i["aura_score"] is None and i["composite_score"] is None and i["mirage_meter"] is None
        assert isinstance(i["chaos_contribution"], float)                    # does not read wins
        assert {a["score"] for a in li["derived_scores_affected"]} == {
            "aura_score", "composite_score", "mirage_meter"}
        assert b["stats"]["wins_total"] == 0.0                               # placeholder, not -1
        assert b["data_quality"]["fields"]["wins"]["basis"] == "invalid_range"
        assert b["data_quality"]["legacy_corrupted_fields"] == ["fighter_w"]

    def test_fractional_wins_rejected(self, engine, real_api):
        c = real_api([_fighter("Frac")])
        _sql(engine, "UPDATE fighters SET wins=7.9 WHERE name='Frac'")
        b = _strict(c.get("/fighter/Frac"))
        assert b["legacy_integrity"]["raw_input_corruption"][0]["field"] == "fighter_w"
        assert b["stats"]["wins_total"] == 0.0

    def test_infinite_slpm_chaos_not_visible_as_trustworthy(self, engine, real_api):
        c = real_api([_fighter("Inf Slpm")])
        _sql(engine, "UPDATE fighters SET slpm=:v WHERE name='Inf Slpm'", v=float("inf"))
        b = _strict(c.get("/fighter/Inf Slpm"))
        assert b["intelligence"]["chaos_contribution"] is None
        aff = {a["score"]: a for a in b["legacy_integrity"]["derived_scores_affected"]}
        assert aff["chaos_contribution"]["depends_on"] == ["fighter_SlpM"]
        assert aff["chaos_contribution"]["legacy_value"] is None
        assert aff["chaos_contribution"]["reason"] == "derived_from_corrupted_inputs"

    def test_three_categories_are_distinct(self, engine, real_api):
        c = real_api([_fighter("All Three")])
        _sql(engine, "UPDATE fighters SET slpm='junk', aura_score='bad' WHERE name='All Three'")
        li = _strict(c.get("/fighter/All Three"))["legacy_integrity"]
        assert [e["field"] for e in li["raw_input_corruption"]] == ["fighter_SlpM"]
        assert [e["field"] for e in li["stored_score_corruption"]] == ["aura_score"]
        assert {a["score"] for a in li["derived_scores_affected"]} == {"aura_score", "chaos_contribution"}

    def test_stored_score_not_derived_from_corrupt_input(self, engine, real_api):
        """A valid stored score is not a heuristic, so corrupt raw inputs do not withhold it."""
        c = real_api([_fighter("Stored Ok")])
        _sql(engine, "UPDATE fighters SET slpm='junk', chaos_contribution=33.0 WHERE name='Stored Ok'")
        b = _strict(c.get("/fighter/Stored Ok"))
        assert b["intelligence"]["chaos_contribution"] == 33.0
        assert "chaos_contribution" not in {a["score"] for a in b["legacy_integrity"]["derived_scores_affected"]}

    def test_integrity_metadata_survives_extension_failure(self, engine, real_api, monkeypatch):
        c = real_api([_fighter("No Ext")])
        _sql(engine, "UPDATE fighters SET slpm='junk' WHERE name='No Ext'")
        monkeypatch.setattr(app_module, "build_profile_extension",
                            lambda e, n: (_ for _ in ()).throw(RuntimeError("boom")))
        b = _strict(c.get("/fighter/No Ext"))
        assert b["data_quality"] is None and b["extension_status"]["reason"] == "ERROR"
        assert b["legacy_integrity"]["raw_input_corruption"][0]["field"] == "fighter_SlpM"
        assert b["intelligence"]["aura_score"] is None

    def test_corruption_logged_without_values(self, engine, real_api, caplog):
        c = real_api([_fighter("Log Me")])
        _sql(engine, "UPDATE fighters SET slpm='junk-secret-value' WHERE name='Log Me'")
        with caplog.at_level(logging.WARNING):
            _strict(c.get("/fighter/Log Me"))
        assert "Log Me" in caplog.text and "fighter_SlpM" in caplog.text
        assert "junk-secret-value" not in caplog.text


# ═══ FIX 3 — nested extension validation ═══════════════════════════════════
def _mut(fn):
    e = copy.deepcopy(_complete_extension())
    fn(e)
    return e


class TestNestedExtensionValidation:
    def test_valid_extension_passes(self):
        validate_extension(_complete_extension())

    @pytest.mark.parametrize("name,fn", [
        ("fields.slpm null", lambda e: e["data_quality"]["fields"].__setitem__("slpm", None)),
        ("field missing keys", lambda e: e["data_quality"]["fields"].__setitem__("slpm", {"value": 1})),
        ("field unknown status", lambda e: e["data_quality"]["fields"]["slpm"].__setitem__("status", "weird")),
        ("field unknown basis", lambda e: e["data_quality"]["fields"]["slpm"].__setitem__("basis", "weird")),
        ("measured w/o value", lambda e: e["data_quality"]["fields"]["slpm"].__setitem__("value", None)),
        ("unavailable w/ value", lambda e: e["data_quality"]["fields"]["career_knockdowns"].__setitem__("value", 3)),
        ("field value nan", lambda e: e["data_quality"]["fields"]["slpm"].__setitem__("value", float("nan"))),
        ("field removed", lambda e: e["data_quality"]["fields"].pop("td_acc")),
        ("coverage null", lambda e: e["data_quality"].__setitem__("coverage", None)),
        ("coverage missing key", lambda e: e["data_quality"]["coverage"].pop("dataset_end")),
        ("coverage count negative", lambda e: e["data_quality"]["coverage"].__setitem__("ufc_fights_in_dataset", -1)),
        ("coverage fraction >1", lambda e: e["data_quality"]["coverage"].__setitem__("methods_available_fraction", 1.5)),
        ("coverage nan", lambda e: e["data_quality"]["coverage"].__setitem__("methods_available_fraction", float("nan"))),
        ("block null", lambda e: e["data_quality"].__setitem__("core_stat_block", None)),
        ("block inconsistent", lambda e: e["data_quality"]["core_stat_block"].__setitem__("available", False)),
        ("block bad status", lambda e: e["data_quality"]["core_stat_block"].__setitem__("status", "great")),
        ("score keys missing", lambda e: e["scores"]["aura"].pop("reason")),
        ("score object missing", lambda e: e["scores"].pop("mirage")),
        ("meta missing", lambda e: e["scores"].pop("meta")),
        ("score not dict", lambda e: e["scores"].__setitem__("composite", 5)),
        ("nonfinite score, available", lambda e: e["scores"]["composite"].__setitem__("value", float("inf"))),
        ("nan score, available", lambda e: e["scores"]["composite"].__setitem__("value", float("nan"))),
        ("null score, available", lambda e: e["scores"]["composite"].__setitem__("value", None)),
        ("score > 100", lambda e: e["scores"]["composite"].__setitem__("value", 150.0)),
        ("score < 0", lambda e: e["scores"]["composite"].__setitem__("value", -1.0)),
        ("nonnull score, unavailable", lambda e: e["scores"]["mirage"].__setitem__("value", 12.0)),
        ("unavailable w/o reason", lambda e: e["scores"]["mirage"].__setitem__("reason", None)),
        ("unavailable w/ empty reason", lambda e: e["scores"]["mirage"].__setitem__("reason", "")),
        ("available not bool", lambda e: e["scores"]["composite"].__setitem__("available", "yes")),
        ("score bad status", lambda e: e["scores"]["composite"].__setitem__("status", "validated")),
    ])
    def test_invalid_payloads_rejected(self, name, fn):
        ext = _mut(fn)
        with pytest.raises(ExtensionValidationError):
            validate_extension(ext)
        out = guard_extension(lambda e, n: ext, object(), "A", LOG)
        assert out["extension_status"] == {"available": False, "reason": "INVALID_SHAPE"}
        assert out["data_quality"] is None and out["scores"] is None

    @pytest.mark.parametrize("bad", [None, [], "x", 7, {}, {"data_quality": {}, "scores": {}}])
    def test_missing_or_partial_extension(self, bad):
        with pytest.raises(ValueError):
            validate_extension(bad)

    def test_builder_valueerror_is_error_not_invalid_shape(self):
        def builder(e, n):
            raise ValueError("builder blew up")
        out = guard_extension(builder, object(), "A", LOG)
        assert out["extension_status"]["reason"] == "ERROR"

    def test_validation_valueerror_is_invalid_shape(self):
        ext = _mut(lambda e: e["scores"]["composite"].__setitem__("value", None))
        assert guard_extension(lambda e, n: ext, object(), "A", LOG)["extension_status"]["reason"] == "INVALID_SHAPE"

    def test_expected_missing_fighter_is_not_found(self):
        assert guard_extension(lambda e, n: None, object(), "A", LOG)["extension_status"]["reason"] == "NOT_FOUND"

    def test_reviewer_injection_endpoint(self, real_api, monkeypatch):
        """The exact reviewer case: slpm null, coverage null, non-finite score with available=true."""
        c = real_api([_fighter("Inject")])
        bad = _complete_extension()
        bad["data_quality"]["fields"]["slpm"] = {"value": None, "status": "measured",
                                                 "basis": "measured", "unit": "x"}
        bad["data_quality"]["coverage"] = None
        bad["scores"]["aura"]["value"] = float("inf")
        monkeypatch.setattr(app_module, "build_profile_extension", lambda e, n: bad)
        b = _strict(c.get("/fighter/Inject"))
        assert b["extension_status"] == {"available": False, "reason": "INVALID_SHAPE"}
        assert b["data_quality"] is None and b["scores"] is None
        assert "intelligence" in b and "stats" in b

    def test_real_extension_validates_for_every_kind_of_fighter(self, engine, real_api):
        c = real_api([_fighter("Normal"),
                      _fighter("Zeros", slpm=0.0, str_acc=0.0, str_def=0.0, td_avg=0.0, td_acc=0.0,
                               td_def=0.0, sub_avg=0.0, height_cm=0.0, reach_cm=0.0, age=0.0),
                      _fighter("Amb", str_def=0.0, td_avg=0.0)])
        _sql(engine, "UPDATE fighters SET reach_cm='junk' WHERE name='Amb'")
        for n in ("Normal", "Zeros", "Amb"):
            b = _strict(c.get(f"/fighter/{n}"))
            assert b["extension_status"] == {"available": True, "reason": None}, n


# ═══ FIX 4 — history retrieval normalisation ═══════════════════════════════
def _fight(r, b, winner, day, method=None):
    return dict(r_name=r, b_name=b, date=dt.date(2024, 1, day), winner=winner, method=method,
                weight_class="Lightweight")


class TestHistoryLookupNormalisation:
    FIGHTS = [
        _fight("  Review Red  ", "Review Blue", "review red", 1),               # stored whitespace; winner variant
        _fight("review blue", "REVIEW  RED", "Review Blue", 2),                 # mixed case, internal double space
        _fight("Review Red", "Third Guy", "Draw", 3),
        _fight("Fourth Guy", "REVIEW BLUE", "No Contest", 4),
        _fight("Review Red", "Fifth Guy", None, 5),
        _fight("Plain One", "Plain Two", "Plain One", 6),
    ]

    @pytest.fixture
    def c(self, real_api):
        return real_api([_fighter("Review Red"), _fighter("Review Blue"),
                         _fighter("Plain One"), _fighter("Plain Two")], fights=self.FIGHTS)

    def test_canonical_name_finds_whitespace_and_case_variants(self, c):
        b = _strict(c.get("/fighter/Review Red/history"))
        assert b["count"] == 4
        assert [f["date"] for f in b["fights"]] == ["2024-01-05", "2024-01-03", "2024-01-02", "2024-01-01"]

    def test_both_viewpoints_and_opponents_and_results(self, c):
        red = {f["date"]: f for f in _strict(c.get("/fighter/Review Red/history"))["fights"]}
        blue = {f["date"]: f for f in _strict(c.get("/fighter/Review Blue/history"))["fights"]}
        assert red["2024-01-01"]["result"] == "W" and blue["2024-01-01"]["result"] == "L"
        assert red["2024-01-01"]["opponent"] == "Review Blue"
        assert blue["2024-01-01"]["opponent"] == "  Review Red  "              # stored display name preserved
        assert red["2024-01-02"]["result"] == "L" and blue["2024-01-02"]["result"] == "W"
        assert red["2024-01-02"]["opponent"] == "review blue"
        assert blue["2024-01-02"]["opponent"] == "REVIEW  RED"
        assert red["2024-01-03"]["result"] == "D"                                # draw
        assert blue["2024-01-04"]["result"] == "NC"                              # no contest
        assert red["2024-01-05"]["result"] == "UNKNOWN"                          # unknown winner
        assert set(blue) == {"2024-01-01", "2024-01-02", "2024-01-04"}

    def test_profile_coverage_uses_the_same_matching(self, c):
        cov = _strict(c.get("/fighter/Review Red"))["data_quality"]["coverage"]
        assert cov["ufc_fights_in_dataset"] == 4
        assert cov["first_dataset_fight"] == "2024-01-01" and cov["last_dataset_fight"] == "2024-01-05"
        h = _strict(c.get("/fighter/Review Red/history"))
        assert cov["ufc_fights_in_dataset"] == h["count"]

    def test_normal_names_unchanged(self, c):
        b = _strict(c.get("/fighter/Plain One/history"))
        assert b["count"] == 1 and b["fights"][0]["opponent"] == "Plain Two" and b["fights"][0]["result"] == "W"
        assert b["name_match"]["stored_spellings"] == ["Plain One"]
        assert b["name_match"]["ambiguous_identity"] is False

    def test_stored_spellings_reported(self, c):
        nm = _strict(c.get("/fighter/Review Red/history"))["name_match"]
        assert set(nm["stored_spellings"]) == {"  Review Red  ", "REVIEW  RED", "Review Red"}

    def test_no_substring_or_fuzzy_matching(self, engine, c):
        with engine.connect() as conn:
            assert fetch_fight_rows(conn, "Review") == []
            assert fetch_fight_rows(conn, "Red") == []
            assert fetch_fight_rows(conn, "Review Re") == []

    def test_documented_limitation_tabs_not_matched_in_sql(self, engine, real_api):
        real_api([_fighter("Tab Guy")], fights=[_fight("Tab\tGuy", "Someone", "Tab\tGuy", 1)])
        with engine.connect() as conn:
            assert fetch_fight_rows(conn, "Tab Guy") == []          # SQL narrows with spaces/case only

    def test_ambiguous_normalised_identity_is_flagged(self, real_api):
        c = real_api([_fighter("Dup Name"), _fighter("dup name")],
                     fights=[_fight("Dup Name", "Other", "Dup Name", 1)])
        nm = _strict(c.get("/fighter/Dup Name/history"))["name_match"]
        assert nm["fighter_rows_matching_name"] == 2 and nm["ambiguous_identity"] is True

    def test_no_rows_still_404(self, real_api):
        c = real_api([_fighter("Lonely")])
        assert c.get("/fighter/Lonely/history").status_code == 404

    def test_history_only_issues_select(self, engine, c):
        from sqlalchemy import event
        seen = []

        @event.listens_for(engine, "before_cursor_execute")
        def cap(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)
        c.get("/fighter/Review Red/history")
        c.get("/fighter/Review Red")
        assert seen and all(s_.lstrip().upper().startswith("SELECT") for s_ in seen)
