"""
FTR-01B1-R1 — regression tests for the Codex review findings.

Pure-function tests plus full FastAPI endpoint tests (TestClient, SQLite
in-memory, mocked predictor).
"""

import datetime as dt
import json
import logging
import math
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as app_module
from main import app
from db.models import Fighter, Fight
from fighter_profile import scores as S
from fighter_profile.availability import (
    CORE_BLOCK, build_fields, core_block_summary, is_usable,
)
from fighter_profile.history import classify_result
from fighter_profile.sanitize import json_safe, sanitize_raw_stats
from fighter_profile.service import (
    build_history, guard_extension, validate_extension,
)
from tests.test_profile_api import COMPLETE, _raw

app.router.on_startup.clear()
app.router.on_shutdown.clear()


def _row(**kw):
    base = dict(wins=18, losses=3, draws=0, age=30.0, height_cm=178.0, reach_cm=182.0,
                weight_lbs=155.0, slpm=4.2, str_acc=0.48, str_def=0.58,
                td_avg=1.2, td_acc=0.40, td_def=0.70, sub_avg=0.3)
    base.update(kw)
    return base


# ═══ CORRECTION 1 — ambiguous takedown zeros ═══════════════════════════════
class TestAmbiguousTakedownZero:
    # Reported defect: 8-4, slpm 2.59, td_avg 0 (outside the all-zero block).
    FIXTURE = dict(wins=8, losses=4, draws=0, slpm=2.59, td_avg=0.0, td_acc=0.0)

    @staticmethod
    def _old_aura(wins, losses, slpm, td_avg):
        """The pre-R1 formula, with td_avg=0 accepted as a measurement."""
        total = wins + losses
        vol = min(1.0, (slpm / 6.0) * 0.5 + (td_avg / 5.0) * 0.5)
        return min(100.0, wins / total * 40.0 + vol * 35.0 + min(total, 20) / 20.0 * 25.0)

    def test_reported_defect_value_reproduced_by_old_formula(self):
        assert round(self._old_aura(8, 4, 2.59, 0.0), 1) == 49.2

    def test_aura_now_unavailable_when_td_avg_zero_is_ambiguous(self):
        f = build_fields(_row(**self.FIXTURE))
        assert f["td_avg"]["status"] == "ambiguous" and f["td_avg"]["value"] == 0.0
        a = S.aura(f)
        assert a["value"] is None and a["available"] is False
        assert a["inputs_missing"] == ["td_avg"]

    def test_is_usable_rejects_every_ambiguous_field(self):
        f = build_fields(_row(td_avg=0.0, td_acc=0.0, td_def=0.0, str_def=0.0, slpm=0.0, str_acc=0.0))
        ambiguous = [k for k, v in f.items() if v["status"] == "ambiguous"]
        assert set(ambiguous) >= {"td_avg", "td_acc", "td_def", "str_def", "slpm", "str_acc"}
        assert not any(is_usable(f[k]) for k in ambiguous)

    def test_attempts_not_inferred_from_landed_rate(self):
        f = build_fields(_row(td_avg=0.0, td_acc=0.0))
        assert f["td_acc"]["status"] == "ambiguous"
        assert "not stored" in f["td_acc"]["note"]

    def test_td_acc_zero_with_positive_td_avg_not_measured(self):
        f = build_fields(_row(td_avg=2.0, td_acc=0.0))
        assert f["td_acc"]["status"] == "ambiguous" and f["td_acc"]["value"] == 0.0

    def test_zero_submissions_remain_measured_zero(self):
        f = build_fields(_row(sub_avg=0.0))
        assert f["sub_avg"]["status"] == "measured_zero" and is_usable(f["sub_avg"])

    def test_positive_td_avg_still_feeds_aura(self):
        assert S.aura(build_fields(_row(td_avg=0.5)))["available"] is True


# ═══ CORRECTION 3 — field validation ═══════════════════════════════════════
class TestValidation:
    @pytest.mark.parametrize("k", ["wins", "losses", "draws"])
    @pytest.mark.parametrize("bad,basis", [
        (-1, "invalid_range"), (7.9, "invalid_range"), (float("nan"), "invalid_value"),
        (float("inf"), "invalid_value"), ("7", "invalid_value"), (True, "invalid_value"),
    ])
    def test_bad_record_counts_rejected_not_truncated(self, k, bad, basis):
        f = build_fields(_row(**{k: bad}))
        assert f[k]["value"] is None and f[k]["status"] == "unavailable"
        assert f[k]["basis"] == basis
        assert f[k]["status"] != "measured"

    def test_whole_float_counts_accepted(self):
        assert build_fields(_row(wins=7.0))["wins"]["value"] == 7

    @pytest.mark.parametrize("k,bad", [
        ("age", 5), ("age", 150), ("age", -3), ("height_cm", 3.0), ("height_cm", 900),
        ("reach_cm", -10), ("reach_cm", 5000), ("weight_lbs", 5), ("weight_lbs", 5000),
    ])
    def test_impossible_physicals_invalid_range_not_source_nan(self, k, bad):
        f = build_fields(_row(**{k: bad}))
        assert f[k]["value"] is None and f[k]["basis"] == "invalid_range"

    @pytest.mark.parametrize("k", ["age", "height_cm", "reach_cm", "weight_lbs"])
    @pytest.mark.parametrize("bad", ["abc", float("nan"), float("inf"), float("-inf")])
    def test_malformed_or_nonfinite_is_invalid_value(self, k, bad):
        f = build_fields(_row(**{k: bad}))
        assert f[k]["value"] is None and f[k]["basis"] == "invalid_value"
        assert f[k]["status"] == "unavailable"

    def test_source_missing_still_source_nan(self):
        f = build_fields(_row(height_cm=0, reach_cm=None))
        assert f["height_cm"]["basis"] == "source_nan" and f["reach_cm"]["basis"] == "source_nan"

    @pytest.mark.parametrize("k,bad", [
        ("slpm", -1.0), ("slpm", 999.0), ("str_acc", 1.5), ("str_def", -0.1),
        ("td_avg", 500.0), ("sub_avg", -2.0),
    ])
    def test_core_out_of_range(self, k, bad):
        f = build_fields(_row(**{k: bad}))
        assert f[k]["value"] is None and f[k]["basis"] == "invalid_range"

    @pytest.mark.parametrize("bad", [float("inf"), float("nan"), "x"])
    def test_core_invalid_value_not_source_nan(self, bad):
        f = build_fields(_row(slpm=bad))
        assert f["slpm"]["basis"] == "invalid_value" and f["slpm"]["value"] is None

    def test_all_garbage_block_is_not_labelled_placeholder_or_source_nan(self):
        f = build_fields(_row(**{k: "garbage" for k in CORE_BLOCK}))
        assert all(f[k]["basis"] == "invalid_value" for k in CORE_BLOCK)
        s = core_block_summary(_row(**{k: "garbage" for k in CORE_BLOCK}), f)
        assert s["available"] is False and s["status"] == "unavailable"
        assert s["invalid_fields"] == list(CORE_BLOCK)

    def test_block_with_one_invalid_field_is_partial_and_not_available(self):
        row = _row(slpm=float("inf"))
        s = core_block_summary(row, build_fields(row))
        assert s["status"] == "partial" and s["available"] is False
        assert s["invalid_fields"] == ["slpm"] and "slpm" not in s["usable_fields"]
        assert "str_acc" in s["usable_fields"]           # partial availability preserved

    def test_block_with_ambiguous_zero_is_partial_not_complete(self):
        row = _row(td_def=0.0)
        s = core_block_summary(row, build_fields(row))
        assert s["status"] == "partial" and s["unconfirmed_fields"] == ["td_def"]

    def test_complete_block_and_placeholder_block(self):
        s = core_block_summary(_row())
        assert s["status"] == "complete" and s["available"] is True and s["basis"] == "measured"
        z = {k: 0.0 for k in CORE_BLOCK}
        s = core_block_summary(_row(**z))
        assert s["status"] == "unavailable" and s["basis"] == "source_placeholder_zero"

    def test_invalid_value_never_marked_measured_anywhere(self):
        row = _row(wins=-1, age="x", height_cm=float("nan"), slpm=-3, str_acc=2, weight_lbs=1)
        for k, v in build_fields(row).items():
            if v["basis"] in ("invalid_value", "invalid_range"):
                assert v["status"] == "unavailable" and v["value"] is None


# ═══ CORRECTION 5 — fight history ══════════════════════════════════════════
class TestHistoryNormalisation:
    @pytest.mark.parametrize("fighter,r,b,winner,expected", [
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "Aaron Pico", "W"),            # red wins
        ("Aaron Pico", "Lerone Murphy", "Aaron Pico", "Aaron Pico", "W"),            # blue wins
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "Lerone Murphy", "L"),
        ("Aaron Pico", "Lerone Murphy", "Aaron Pico", "Lerone Murphy", "L"),
        ("Aaron Pico", "Aaron  Pico ", "Lerone Murphy", " aaron pico", "W"),          # whitespace/case
        ("aaron pico", "AARON PICO", "Lerone Murphy", "LERONE   MURPHY", "L"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", " draw ", "D"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "No Contest", "NC"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "NO  CONTEST", "NC"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", None, "UNKNOWN"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "   ", "UNKNOWN"),
        ("Aaron Pico", "Aaron Pico", "Lerone Murphy", "Somebody Else", "UNKNOWN"),
        ("Aaron Pico", "X", "Y", "Aaron Pico", "UNKNOWN"),                           # not on card
    ])
    def test_classify(self, fighter, r, b, winner, expected):
        assert classify_result(fighter, r, b, winner) == expected

    def _row(self, **kw):
        base = dict(r_name="Aaron  Pico", b_name="Lerone Murphy", date=dt.date(2025, 8, 16),
                    winner="aaron pico", method=None, weight_class="Featherweight")
        base.update(kw)
        return SimpleNamespace(**base)

    def test_display_names_preserved_and_opponent_resolved(self):
        h = build_history("Aaron Pico", [self._row()])
        f = h["fights"][0]
        assert f["result"] == "W" and f["opponent"] == "Lerone Murphy"
        h = build_history("Lerone Murphy", [self._row()])
        assert h["fights"][0]["opponent"] == "Aaron  Pico"            # original display name

    @pytest.mark.parametrize("m", [None, "", "   ", "\t\n"])
    def test_empty_or_whitespace_method_is_empty_and_unavailable(self, m):
        f = build_history("Aaron Pico", [self._row(method=m)])["fights"][0]
        assert f["method"] == "" and f["method_available"] is False

    def test_method_present_is_stripped_and_available_never_inferred(self):
        f = build_history("Aaron Pico", [self._row(method=" KO/TKO ")])["fights"][0]
        assert f["method"] == "KO/TKO" and f["method_available"] is True
        g = build_history("Aaron Pico", [self._row(method=None)])
        assert all("decision" not in f["method"].lower() for f in g["fights"])
        assert g["fights"][0]["method"] == "" and g["fights"][0]["method_available"] is False
        assert g["methods_available_fraction"] == 0.0

    def test_scope_documents_latest_20_window(self):
        h = build_history("Aaron Pico", [self._row() for _ in range(20)])
        assert h["history_scope"]["window"] == "latest_20_fights"
        assert h["history_scope"]["may_be_truncated"] is True
        assert "result_counts" in h["history_scope"]["applies_to"]
        assert build_history("Aaron Pico", [self._row()])["history_scope"]["may_be_truncated"] is False


# ═══ CORRECTION 4 — extension guard (unit) ═════════════════════════════════
def _complete_extension():
    from fighter_profile.service import build_coverage
    row = _row()
    f = build_fields(row)
    cov = build_coverage("A", {"row": {"last_fight_date": None}, "fights": [], "dataset_end": None})
    return {
        "data_quality": {"schema": "x", "fields": f, "core_stat_block": core_block_summary(row, f),
                         "coverage": cov, "legacy_compat": {}},
        "scores": S.build_scores(f),
    }


class TestGuardExtension:
    log = logging.getLogger("t")

    def test_complete_extension_passes_through(self):
        ext = _complete_extension()
        out = guard_extension(lambda e, n: ext, object(), "A", self.log)
        assert out["extension_status"] == {"available": True, "reason": None}
        assert out["data_quality"] is ext["data_quality"] and out["scores"] is ext["scores"]

    def test_missing_extension_is_not_found(self, caplog):
        with caplog.at_level(logging.WARNING):
            out = guard_extension(lambda e, n: None, object(), "Ghost", self.log)
        assert out["extension_status"]["reason"] == "NOT_FOUND"
        assert out["data_quality"] is None and out["scores"] is None
        assert "Ghost" in caplog.text

    @pytest.mark.parametrize("mutate", [
        lambda e: e.pop("scores"),
        lambda e: e["scores"].pop("mirage"),
        lambda e: e["data_quality"].pop("fields"),
        lambda e: e["data_quality"]["fields"].pop("slpm"),
        lambda e: e["scores"].__setitem__("aura", {"value": 1}),
        lambda e: e.__setitem__("data_quality", "oops"),
    ])
    def test_partial_extension_is_invalid_shape_not_a_crash(self, mutate):
        ext = _complete_extension()
        mutate(ext)
        out = guard_extension(lambda e, n: ext, object(), "A", self.log)
        assert out["extension_status"] == {"available": False, "reason": "INVALID_SHAPE"}
        assert out["data_quality"] is None and out["scores"] is None

    @pytest.mark.parametrize("bad", [[], "x", 5, {}])
    def test_bad_values_rejected(self, bad):
        with pytest.raises(ValueError):
            validate_extension(bad)
        out = guard_extension(lambda e, n: bad, object(), "A", self.log)
        assert out["extension_status"]["available"] is False

    def test_raised_exception_degrades_and_logs_no_secrets(self, caplog):
        secret = "postgresql://user:SUPERSECRET@db.example.com/prod"

        def boom(e, n):
            raise RuntimeError(secret)

        with caplog.at_level(logging.WARNING):
            out = guard_extension(boom, object(), "Aaron Pico", self.log)
        assert out["extension_status"] == {"available": False, "reason": "ERROR"}
        assert "Aaron Pico" in caplog.text and "RuntimeError" in caplog.text
        assert "SUPERSECRET" not in caplog.text and "postgresql://" not in caplog.text

    def test_no_engine_degrades(self):
        out = guard_extension(lambda e, n: _complete_extension(), None, "A", self.log)
        assert out["extension_status"]["reason"] == "ERROR"


# ═══ Endpoint fixtures ═════════════════════════════════════════════════════
def _fighter(name, **kw):
    d = dict(COMPLETE)
    d.update(name=name, **kw)
    return d


@pytest.fixture
def api(engine):
    """Factory: api(fighters, fights=(), raw_overrides=None) -> TestClient."""
    clients = []

    def make(fighters, fights=(), raw_overrides=None):
        with Session(engine) as s:
            for d in fighters:
                s.add(Fighter(latest_features={"r_fighter_SlpM": 1.0}, **d))
            for f in fights:
                s.add(Fight(**f))
            s.commit()
        by_name = {d["name"]: d for d in fighters}
        predictor = MagicMock()
        predictor.search_fighter.side_effect = lambda n: n if n in by_name else None

        def raw(n):
            r = _raw(by_name[n])
            r.update((raw_overrides or {}))
            return r
        predictor.feature_calculator.get_latest_fighter_stats.side_effect = raw
        app_module.engine = engine
        app_module.predictor = predictor
        app_module.orchestrator = MagicMock()
        c = TestClient(app, raise_server_exceptions=False)
        clients.append(c)
        return c

    yield make
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None


def _assert_strict_json(resp):
    """Standards-compliant JSON: no NaN/Infinity tokens."""
    assert resp.status_code == 200, resp.text
    for tok in ("NaN", "Infinity"):
        assert tok not in resp.text
    return json.loads(resp.text, parse_constant=lambda c: pytest.fail(f"non-standard constant {c}"))


# ═══ CORRECTION 2 — non-finite legacy values (endpoint) ════════════════════
class TestNonFiniteEndpoint:
    @pytest.mark.parametrize("bad", [float("inf"), float("-inf"), float("nan")])
    def test_legacy_raw_nonfinite_slpm_returns_valid_json_200(self, api, bad):
        c = api([_fighter("Bad Slpm")], raw_overrides={"fighter_SlpM": bad})
        body = _assert_strict_json(c.get("/fighter/Bad Slpm"))
        assert body["stats"]["SLpM_total"] == 0.0                # exceptional legacy placeholder
        assert body["data_quality"]["legacy_corrupted_fields"] == ["fighter_SlpM"]
        assert "legacy.corrupt_values" in body["data_quality"]["legacy_compat"]

    def test_db_infinite_slpm_is_invalid_value_and_never_trusted(self, api):
        c = api([_fighter("Inf Fighter", slpm=float("inf"))],
                raw_overrides={"fighter_SlpM": float("inf")})
        body = _assert_strict_json(c.get("/fighter/Inf Fighter"))
        f = body["data_quality"]["fields"]["slpm"]
        assert f["value"] is None and f["basis"] == "invalid_value" and f["status"] == "unavailable"
        sc = body["scores"]
        assert sc["aura"]["available"] is False and "slpm" in sc["aura"]["inputs_missing"]
        assert sc["chaos_contribution"]["available"] is False
        assert body["data_quality"]["core_stat_block"]["status"] == "partial"
        assert body["data_quality"]["core_stat_block"]["available"] is False

    def test_malformed_string_raw_value(self, api):
        c = api([_fighter("Str Fighter")], raw_overrides={"fighter_TD_Avg": "garbage"})
        body = _assert_strict_json(c.get("/fighter/Str Fighter"))
        assert body["stats"]["td_avg_total"] == 0.0
        assert body["data_quality"]["legacy_corrupted_fields"] == ["fighter_TD_Avg"]

    def test_all_raw_nonfinite_does_not_manufacture_measured_zero(self, api):
        bad = {k: float("nan") for k in (
            "fighter_SlpM", "fighter_Str_Acc", "fighter_Str_Def", "fighter_TD_Avg",
            "fighter_TD_Acc", "fighter_TD_Def", "fighter_Sub_Avg")}
        c = api([_fighter("All Bad", slpm=float("inf"))], raw_overrides=bad)
        body = _assert_strict_json(c.get("/fighter/All Bad"))
        for f in body["data_quality"]["fields"].values():
            assert f["status"] != "measured_zero"
        # legacy zeros are only the legacy placeholder; the new layer reads the DB independently
        assert body["stats"]["SLpM_total"] == 0.0 and body["stats"]["td_avg_total"] == 0.0
        assert body["data_quality"]["fields"]["slpm"]["basis"] == "invalid_value"
        assert body["scores"]["aura"]["available"] is False

    def test_valid_legacy_response_values_and_types_unchanged(self, api):
        c = api([_fighter("Good One")])
        body = _assert_strict_json(c.get("/fighter/Good One"))
        assert body["stats"]["SLpM_total"] == 4.2 and isinstance(body["stats"]["SLpM_total"], float)
        assert body["stats"]["sig_str_acc_total"] == pytest.approx(48.0)
        assert body["stats"]["wins_total"] == 18.0
        assert body["data_quality"]["legacy_corrupted_fields"] == []
        assert set(body["intelligence"]) == {
            "style", "is_active", "aura_score", "composite_score", "chaos_contribution",
            "mirage_meter", "scores_source"}
        assert body["extension_status"] == {"available": True, "reason": None}

    def test_json_safe_helper(self):
        out = json_safe({"a": float("inf"), "b": [float("nan"), 1.5, 2, True, None, "x"], "c": {"d": -math.inf}})
        assert out == {"a": None, "b": [None, 1.5, 2, True, None, "x"], "c": {"d": None}}
        v = {"x": 1.25, "y": 3}
        assert json_safe(v) == v

    def test_sanitize_raw_stats_preserves_valid_values_exactly(self):
        raw = {"a": 1.5, "b": 0.0, "c": None, "d": 7, "e": "3.5", "f": float("inf"), "g": "x"}
        clean, bad = sanitize_raw_stats(raw)
        assert bad == ["f", "g"]
        assert clean["a"] == 1.5 and clean["d"] == 7 and clean["e"] == "3.5" and clean["c"] is None
        assert clean["f"] is None and clean["g"] is None
        assert raw["f"] == float("inf")                       # input untouched


# ═══ CORRECTION 4 — extension failure (endpoint) ═══════════════════════════
class TestExtensionEndpoint:
    def test_complete_extension(self, api):
        c = api([_fighter("Ext A")])
        b = c.get("/fighter/Ext A").json()
        assert b["extension_status"]["available"] is True
        assert b["data_quality"] and b["scores"]

    def test_missing_extension_row(self, api, monkeypatch):
        c = api([_fighter("Ext B")])
        monkeypatch.setattr(app_module, "build_profile_extension", lambda e, n: None)
        r = c.get("/fighter/Ext B")
        b = _assert_strict_json(r)
        assert b["data_quality"] is None and b["scores"] is None
        assert b["extension_status"] == {"available": False, "reason": "NOT_FOUND"}
        assert "intelligence" in b and "stats" in b          # legacy response preserved

    @pytest.mark.parametrize("partial", [
        {"data_quality": {"schema": "x"}, "scores": {}},
        {"scores": {}},
        {"data_quality": None, "scores": None},
        "not a dict",
    ])
    def test_partial_extension_is_200_not_500(self, api, monkeypatch, partial):
        c = api([_fighter("Ext C")])
        monkeypatch.setattr(app_module, "build_profile_extension", lambda e, n: partial)
        b = _assert_strict_json(c.get("/fighter/Ext C"))
        assert b["extension_status"]["reason"] == "INVALID_SHAPE"
        assert b["data_quality"] is None and b["scores"] is None

    def test_raised_exception_and_no_legacy_substitution(self, api, monkeypatch, caplog):
        c = api([_fighter("Ext D")])

        def boom(e, n):
            raise RuntimeError("postgresql://u:PW@h/db")
        monkeypatch.setattr(app_module, "build_profile_extension", boom)
        with caplog.at_level(logging.WARNING):
            b = _assert_strict_json(c.get("/fighter/Ext D"))
        assert b["extension_status"] == {"available": False, "reason": "ERROR"}
        assert b["scores"] is None                           # legacy scores NOT substituted
        assert "Ext D" in caplog.text and "PW@" not in caplog.text

    def test_valid_legacy_response_preserved_when_extension_unavailable(self, api, monkeypatch):
        c = api([_fighter("Ext E")])
        full = c.get("/fighter/Ext E").json()
        monkeypatch.setattr(app_module, "build_profile_extension", lambda e, n: None)
        degraded = c.get("/fighter/Ext E").json()
        assert degraded["stats"] == full["stats"]
        assert degraded["intelligence"] == full["intelligence"]


# ═══ CORRECTION 5 — history endpoint ═══════════════════════════════════════
class TestHistoryEndpoint:
    def test_case_whitespace_and_methods(self, api):
        fights = [
            dict(r_name="Name One", b_name="Other", date=dt.date(2024, 1, 1),
                 winner="  NAME   one ", method="   ", weight_class="Lightweight"),
            dict(r_name="Other", b_name="Name One", date=dt.date(2023, 1, 1),
                 winner="other", method=None, weight_class="Lightweight"),
        ]
        c = api([_fighter("Name One")], fights=fights)
        b = c.get("/fighter/Name One/history").json()
        assert [f["result"] for f in b["fights"]] == ["W", "L"]
        assert all(f["method"] == "" and f["method_available"] is False for f in b["fights"])
        assert b["history_scope"]["window"] == "latest_20_fights"
        assert b["result_counts"] == {"W": 1, "L": 1, "D": 0, "NC": 0, "UNKNOWN": 0}

    def test_window_is_really_20_rows(self, api):
        fights = [dict(r_name="Busy", b_name=f"Opp {i}", date=dt.date(2000, 1, 1) + dt.timedelta(days=i),
                       winner="Busy", method=None, weight_class="Lightweight") for i in range(25)]
        c = api([_fighter("Busy")], fights=fights)
        b = c.get("/fighter/Busy/history").json()
        assert b["count"] == 20 and b["history_scope"]["rows_returned"] == 20
        assert b["history_scope"]["may_be_truncated"] is True
        assert b["result_counts"]["W"] == 20                  # counts describe returned rows only


# ═══ CORRECTION 6 — Mirage withheld ════════════════════════════════════════
class TestMirageWithheld:
    def test_endpoint_mirage_withheld_even_with_complete_data(self, api):
        c = api([_fighter("Mirage Case", wins=16, losses=4, str_def=0.40)])
        m = c.get("/fighter/Mirage Case").json()["scores"]["mirage"]
        assert m["value"] is None and m["available"] is False and m["status"] == "unavailable"
        assert m["reason"] == "UNVALIDATED_HEURISTIC"
        assert {"opposition_quality", "resume_inflation"} <= set(m["unsupported_claims"])

    def test_legacy_mirage_meter_untouched(self, api):
        c = api([_fighter("Mirage Case", wins=16, losses=4, str_def=0.40)])
        body = c.get("/fighter/Mirage Case").json()
        assert isinstance(body["intelligence"]["mirage_meter"], float)
        assert body["intelligence"]["mirage_meter"] > 0       # legacy value preserved (known incorrect)

    def test_other_scores_remain_provisional(self, api):
        c = api([_fighter("Plain")])
        sc = c.get("/fighter/Plain").json()["scores"]
        for k in ("composite", "aura", "chaos_contribution"):
            assert sc[k]["status"] == "provisional" and sc[k]["validated"] is False
