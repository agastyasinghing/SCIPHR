"""
FTR-01B1 — GET /fighter/{name} additive contract and /fighter/{name}/history semantics.

SQLite in-memory engine; predictor is a MagicMock (never the real model).
"""

import datetime as dt
import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main as app_module
from main import app
from db.models import Fighter, Fight

app.router.on_startup.clear()
app.router.on_shutdown.clear()

PICO = dict(name="Aaron Pico", wins=13, losses=4, draws=0, age=28.0, height_cm=0.0,
            reach_cm=0.0, weight_lbs=145.0, weight_class="Featherweight",
            slpm=0.0, str_acc=0.0, str_def=0.0, td_avg=0.0, td_acc=0.0, td_def=0.0,
            sub_avg=0.0, last_fight_date=dt.date(2025, 8, 16))
COMPLETE = dict(name="Complete Fighter", wins=18, losses=3, draws=0, age=30.0, height_cm=178.0,
                reach_cm=182.0, weight_lbs=155.0, weight_class="Lightweight",
                slpm=4.2, str_acc=0.48, str_def=0.58, td_avg=1.2, td_acc=0.4, td_def=0.7,
                sub_avg=0.3, last_fight_date=dt.date(2024, 5, 1))
MODEL_FEATURES = {"r_fighter_SlpM": 0.0, "r_knockdowns": 0.0, "r_ctrl_time_sec": 121.0}


def _raw(d):
    return {
        "fighter_w": d["wins"], "fighter_l": d["losses"], "fighter_d": d["draws"],
        "age": d["age"], "fighter_height_cm": d["height_cm"], "fighter_reach_cm": d["reach_cm"],
        "fighter_weight_lbs": d["weight_lbs"], "fighter_SlpM": d["slpm"],
        "fighter_Str_Acc": d["str_acc"], "fighter_Str_Def": d["str_def"],
        "fighter_TD_Avg": d["td_avg"], "fighter_TD_Acc": d["td_acc"],
        "fighter_TD_Def": d["td_def"], "fighter_Sub_Avg": d["sub_avg"], "knockdowns": 0.0,
    }


@pytest.fixture
def seeded(engine):
    with Session(engine) as s:
        for d in (PICO, COMPLETE):
            s.add(Fighter(latest_features=dict(MODEL_FEATURES), **d))
        s.add(Fight(r_name="Lerone Murphy", b_name="Aaron Pico", date=dt.date(2025, 8, 16),
                    winner="Lerone Murphy", method=None, weight_class="Featherweight"))
        s.add(Fight(r_name="Complete Fighter", b_name="Someone", date=dt.date(2024, 5, 1),
                    winner="Complete Fighter", method=None, weight_class="Lightweight"))
        s.add(Fight(r_name="Zachary Reese", b_name="Sedriques Dumas", date=dt.date(2025, 9, 13),
                    winner="No Contest", method=None, weight_class="Welterweight"))
        s.add(Fight(r_name="Draw A", b_name="Draw B", date=dt.date(2020, 1, 1),
                    winner="Draw", method=None, weight_class="Lightweight"))
        s.add(Fight(r_name="Unk A", b_name="Unk B", date=dt.date(2020, 2, 1),
                    winner=None, method=None, weight_class="Lightweight"))
        s.add(Fight(r_name="Other", b_name="Unk B", date=dt.date(2020, 3, 1),
                    winner="Third Person", method="KO/TKO", weight_class="Lightweight"))
        s.commit()
    return engine


@pytest.fixture
def client(seeded):
    by_name = {d["name"]: d for d in (PICO, COMPLETE)}
    predictor = MagicMock()
    predictor.search_fighter.side_effect = lambda n: n if n in by_name else None
    predictor.feature_calculator.get_latest_fighter_stats.side_effect = lambda n: _raw(by_name[n])
    app_module.engine = seeded
    app_module.predictor = predictor
    app_module.orchestrator = MagicMock()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app_module.engine = None
    app_module.predictor = None
    app_module.orchestrator = None


class TestProfileContract:
    def test_legacy_top_level_keys_preserved_and_new_keys_added(self, client):
        body = client.get("/fighter/Aaron Pico").json()
        assert {"name", "stats", "intelligence"} <= set(body)
        assert {"data_quality", "scores"} <= set(body)

    def test_legacy_stats_and_intelligence_keys_and_types_unchanged(self, client):
        body = client.get("/fighter/Complete Fighter").json()
        assert set(body["stats"]) == {
            "wins_total", "losses_total", "draw", "age", "height", "reach", "weight",
            "weight_class", "SLpM_total", "sig_str_acc_total", "sig_str_def_total",
            "total_knockdowns", "td_avg_total", "td_acc_total", "td_def_total", "sub_avg_total"}
        assert set(body["intelligence"]) == {
            "style", "is_active", "aura_score", "composite_score",
            "chaos_contribution", "mirage_meter", "scores_source"}
        assert isinstance(body["intelligence"]["composite_score"], float)
        assert isinstance(body["stats"]["SLpM_total"], float)
        assert body["stats"]["sig_str_acc_total"] == pytest.approx(48.0)   # still 0-100 (legacy)

    def test_pico_new_objects_are_honest(self, client):
        body = client.get("/fighter/Aaron Pico").json()
        dq, sc = body["data_quality"], body["scores"]
        f = dq["fields"]
        assert f["height_cm"]["value"] is None and f["reach_cm"]["value"] is None
        assert f["slpm"]["value"] is None and f["slpm"]["basis"] == "source_placeholder_zero"
        assert f["career_knockdowns"]["status"] == "not_stored"
        assert dq["core_stat_block"]["available"] is False
        for name in ("composite", "aura", "chaos_contribution", "mirage"):
            assert sc[name]["value"] is None and sc[name]["available"] is False
        cov = dq["coverage"]
        assert cov["ufc_fights_in_dataset"] == 1
        assert cov["record_scope"] == "scraped_career_record" and cov["record_as_of"] is None
        assert cov["methods_available_fraction"] == 0.0
        assert cov["last_dataset_fight"] == "2025-08-16"
        assert cov["age_basis"] == "age_at_last_recorded_bout"

    def test_dataset_end_comes_from_fights_table(self, client):
        cov = client.get("/fighter/Aaron Pico").json()["data_quality"]["coverage"]
        assert cov["dataset_end"] == "2025-09-13"   # max(date) of seeded fights

    def test_legacy_pico_values_documented_as_known_incorrect(self, client):
        body = client.get("/fighter/Aaron Pico").json()
        # legacy behaviour is intentionally unchanged ...
        assert body["intelligence"]["composite_score"] == 100.0
        assert body["intelligence"]["style"] == "STRIKER"
        # ... and the new object flags it
        compat = body["data_quality"]["legacy_compat"]
        assert "saturates" in compat["intelligence.composite_score"]
        assert "STRIKER" in compat["intelligence.style"]

    def test_complete_fighter_scores_available(self, client):
        sc = client.get("/fighter/Complete Fighter").json()["scores"]
        assert sc["composite"]["value"] == 66.1 and sc["composite"]["value"] != 100.0
        assert all(sc[k]["provenance"] == "heuristic" for k in
                   ("composite", "aura", "chaos_contribution", "mirage"))

    def test_extension_failure_degrades_to_null_not_500(self, client, monkeypatch):
        monkeypatch.setattr(app_module, "build_profile_extension",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        r = client.get("/fighter/Complete Fighter")
        assert r.status_code == 200
        assert r.json()["data_quality"] is None and r.json()["scores"] is None
        assert "intelligence" in r.json()


class TestHistorySemantics:
    def test_no_contest_is_nc_for_both_fighters(self, client):
        a = client.get("/fighter/Zachary Reese/history").json()
        b = client.get("/fighter/Sedriques Dumas/history").json()
        assert a["fights"][0]["result"] == "NC" and b["fights"][0]["result"] == "NC"
        assert a["result_counts"]["NC"] == 1 and a["result_counts"]["L"] == 0

    def test_draw_is_d_for_both(self, client):
        for n in ("Draw A", "Draw B"):
            assert client.get(f"/fighter/{n}/history").json()["fights"][0]["result"] == "D"

    def test_missing_or_unattributable_winner_is_unknown_not_loss(self, client):
        assert client.get("/fighter/Unk A/history").json()["fights"][0]["result"] == "UNKNOWN"
        fights = client.get("/fighter/Other/history").json()["fights"]
        assert fights[0]["result"] == "UNKNOWN"

    def test_win_and_loss_unchanged(self, client):
        assert client.get("/fighter/Aaron Pico/history").json()["fights"][0]["result"] == "L"
        assert client.get("/fighter/Lerone Murphy/history").json()["fights"][0]["result"] == "W"

    def test_legacy_fields_preserved_and_methods_not_inferred(self, client):
        body = client.get("/fighter/Aaron Pico/history").json()
        assert {"name", "fights", "count"} <= set(body)
        f = body["fights"][0]
        assert {"opponent", "date", "result", "method", "weight_class"} <= set(f)
        assert f["method"] == "" and f["method_available"] is False
        assert body["methods_available_fraction"] == 0.0
        assert body["count"] == 1

    def test_method_available_when_present(self, client):
        f = client.get("/fighter/Other/history").json()["fights"][0]
        assert f["method"] == "KO/TKO" and f["method_available"] is True


class TestReadOnly:
    def test_profile_and_history_issue_only_select_and_never_read_latest_features(self, seeded, client):
        seen = []

        @event.listens_for(seeded, "before_cursor_execute")
        def _capture(conn, cursor, statement, parameters, context, executemany):
            seen.append(statement)

        client.get("/fighter/Aaron Pico")
        client.get("/fighter/Aaron Pico/history")
        assert seen
        from fighter_profile import service
        for stmt in seen:
            assert stmt.lstrip().upper().startswith("SELECT"), stmt
        for sql in (service._FIGHTER_SQL, service._FIGHTS_SQL, service._DATASET_END_SQL):
            assert "latest_features" not in str(sql)

    def test_latest_features_unchanged_after_requests(self, seeded, client):
        before = {n: v for n, v in seeded.connect().execute(
            text("SELECT name, latest_features FROM fighters ORDER BY name")).fetchall()}
        for path in ("/fighter/Aaron Pico", "/fighter/Complete Fighter",
                     "/fighter/Aaron Pico/history"):
            client.get(path)
        after = {n: v for n, v in seeded.connect().execute(
            text("SELECT name, latest_features FROM fighters ORDER BY name")).fetchall()}
        assert before == after and before
