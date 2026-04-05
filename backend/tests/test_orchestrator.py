"""
Tests for intelligence/orchestrator.py

Covers:
  [4]  _safe_compute returns None on module exception
  [5]  _safe_compute returns result on success
  [6]  _build_context: DB query returns correct FighterContext
  [7]  compute() returns IntelligenceResult even when all modules fail
  [24] fighter with 0 historical fights in DB (new fighter edge case)
  [25] latest_features=NULL logs warning, does not raise
"""

import json
import logging

import pytest
from sqlalchemy import text

from intelligence.models import (
    ChaosResult,
    FighterContext,
    IntelligenceResult,
    ValueBetResult,
)
from intelligence.orchestrator import IntelligenceOrchestrator


# ---------------------------------------------------------------------------
# Helpers for seeding DB fixtures
# ---------------------------------------------------------------------------

def _seed_fighter(conn, name, wins=10, losses=2, slpm=4.5, sub_avg=0.5,
                  td_avg=2.0, str_acc=0.45, str_def=0.58, latest_features=None):
    """Insert a minimal fighter row into SQLite test DB."""
    conn.execute(
        text("""
            INSERT INTO fighters
              (name, wins, losses, draws, age, weight_lbs, height_cm, reach_cm,
               weight_class, slpm, str_acc, str_def, td_avg, td_acc, td_def,
               sub_avg, latest_features)
            VALUES
              (:name, :wins, :losses, 0, 28.0, 155.0, 175.0, 178.0,
               'Lightweight', :slpm, :str_acc, :str_def, :td_avg, 0.50, 0.65,
               :sub_avg, :lf)
        """),
        {
            "name": name, "wins": wins, "losses": losses,
            "slpm": slpm, "str_acc": str_acc, "str_def": str_def,
            "td_avg": td_avg, "sub_avg": sub_avg,
            "lf": json.dumps({"r_slpm": slpm}) if latest_features is None else latest_features,
        },
    )


def _seed_fight(conn, r_name, b_name, winner, method, date="2023-06-01"):
    conn.execute(
        text("""
            INSERT INTO fights (r_name, b_name, date, winner, method, weight_class)
            VALUES (:r, :b, :d, :w, :m, 'Lightweight')
        """),
        {"r": r_name, "b": b_name, "d": date, "w": winner, "m": method},
    )


# ---------------------------------------------------------------------------
# _safe_compute
# ---------------------------------------------------------------------------

class TestSafeCompute:
    def test_returns_result_on_success(self, engine):
        orch = IntelligenceOrchestrator(engine)

        def good_fn(a, b):
            return ChaosResult(score=55.0, tier="HIGH")

        result = orch._safe_compute(good_fn, "x", "y", module_name="test")
        assert result is not None
        assert isinstance(result, ChaosResult)
        assert result.score == 55.0

    def test_returns_none_on_exception(self, engine):
        orch = IntelligenceOrchestrator(engine)

        def bad_fn():
            raise ValueError("something went wrong")

        result = orch._safe_compute(bad_fn, module_name="test_bad")
        assert result is None

    def test_returns_none_on_not_implemented(self, engine):
        orch = IntelligenceOrchestrator(engine)

        def stub_fn():
            raise NotImplementedError("not built yet")

        result = orch._safe_compute(stub_fn, module_name="stub")
        assert result is None

    def test_logs_error_on_exception(self, engine, caplog):
        orch = IntelligenceOrchestrator(engine)

        def bad_fn():
            raise RuntimeError("test error")

        with caplog.at_level(logging.ERROR, logger="intelligence.orchestrator"):
            orch._safe_compute(bad_fn, module_name="failing_module")

        assert "failing_module" in caplog.text

    def test_does_not_log_error_for_not_implemented(self, engine, caplog):
        # NotImplementedError is expected (stubs) — logged at DEBUG, not ERROR
        orch = IntelligenceOrchestrator(engine)

        def stub_fn():
            raise NotImplementedError("stub")

        with caplog.at_level(logging.ERROR, logger="intelligence.orchestrator"):
            orch._safe_compute(stub_fn, module_name="expected_stub")

        # Should NOT log an ERROR for NotImplementedError
        assert "ERROR" not in caplog.text or "expected_stub" not in caplog.text


# ---------------------------------------------------------------------------
# _build_context
# ---------------------------------------------------------------------------

class TestBuildContext:
    def test_returns_fighter_context_with_stats(self, engine):
        with engine.begin() as conn:
            _seed_fighter(conn, "Alpha", wins=15, losses=3, slpm=5.2, sub_avg=1.8)

        orch = IntelligenceOrchestrator(engine)
        ctx = orch._build_context("Alpha")

        assert isinstance(ctx, FighterContext)
        assert ctx.name == "Alpha"
        assert ctx.wins == 15
        assert ctx.losses == 3
        assert ctx.stats["slpm"] == pytest.approx(5.2)
        assert ctx.stats["sub_avg"] == pytest.approx(1.8)

    def test_loads_fight_history(self, engine):
        with engine.begin() as conn:
            _seed_fighter(conn, "Beta")
            _seed_fight(conn, "Beta", "Opp1", "Beta", "KO/TKO", "2024-01-01")
            _seed_fight(conn, "Opp2", "Beta", "Beta", "Submission", "2023-06-01")
            _seed_fight(conn, "Beta", "Opp3", "Opp3", "Decision - Unanimous", "2022-11-01")

        orch = IntelligenceOrchestrator(engine)
        ctx = orch._build_context("Beta")

        assert len(ctx.fights) == 3
        # Most recent fight is first (date DESC)
        assert ctx.fights[0]["winner"] == "Beta"
        assert ctx.fights[0]["method"] == "KO/TKO"

    def test_raises_for_unknown_fighter(self, engine):
        orch = IntelligenceOrchestrator(engine)
        with pytest.raises(ValueError, match="not found"):
            orch._build_context("Nobody McUnknown")

    def test_null_latest_features_logs_warning(self, engine, caplog):
        # [25] Critical gap: latest_features=NULL should warn, not raise
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO fighters
                      (name, wins, losses, draws, age, weight_lbs, height_cm, reach_cm,
                       weight_class, slpm, str_acc, str_def, td_avg, td_acc, td_def,
                       sub_avg, latest_features)
                    VALUES
                      ('NullFeatFighter', 5, 2, 0, 25.0, 155.0, 170.0, 172.0,
                       'Lightweight', 3.5, 0.42, 0.55, 2.0, 0.48, 0.62, 0.8, NULL)
                """),
            )

        orch = IntelligenceOrchestrator(engine)
        with caplog.at_level(logging.WARNING, logger="intelligence.orchestrator"):
            ctx = orch._build_context("NullFeatFighter")

        # Should still return a valid FighterContext
        assert ctx.name == "NullFeatFighter"
        # Should have logged a warning
        assert "NULL" in caplog.text or "latest_features" in caplog.text

    def test_zero_fight_history_returns_empty_fights(self, engine):
        # [24] New fighter with no fight history
        with engine.begin() as conn:
            _seed_fighter(conn, "NewFighter", wins=0, losses=0)

        orch = IntelligenceOrchestrator(engine)
        ctx = orch._build_context("NewFighter")

        assert ctx.fights == []
        assert ctx.wins == 0


# ---------------------------------------------------------------------------
# compute() — full orchestration (stubs active, modules return None)
# ---------------------------------------------------------------------------

class TestOrchestratorCompute:
    def test_returns_intelligence_result_with_stubs(self, engine):
        """
        With all modules raising NotImplementedError (stubs), compute()
        should still return a valid IntelligenceResult — never raise.
        """
        with engine.begin() as conn:
            _seed_fighter(conn, "F1")
            _seed_fighter(conn, "F2")

        orch = IntelligenceOrchestrator(engine)
        result = orch.compute(
            f1_name="F1",
            f2_name="F2",
            model_probs=(0.55, 0.45),
        )

        assert isinstance(result, IntelligenceResult)

    def test_all_modules_return_results(self, engine):
        """All modules return real results now (Opus formulas implemented)."""
        with engine.begin() as conn:
            _seed_fighter(conn, "FA")
            _seed_fighter(conn, "FB")

        orch = IntelligenceOrchestrator(engine)
        result = orch.compute("FA", "FB", (0.60, 0.40))

        assert result.chaos is not None
        assert result.perception_gap is not None
        assert result.fight_dna is not None
        assert result.false_consensus is not None
        assert result.nightmare is not None
        assert result.win_path is not None

    def test_value_bet_always_no_odds_for_ad_hoc(self, engine):
        """value_bet should always be ValueBetResult(NO_ODDS) for ad-hoc calls."""
        with engine.begin() as conn:
            _seed_fighter(conn, "FC")
            _seed_fighter(conn, "FD")

        orch = IntelligenceOrchestrator(engine)
        result = orch.compute("FC", "FD", (0.50, 0.50), fight_id=None)

        assert isinstance(result.value_bet, ValueBetResult)
        assert result.value_bet.signal == "NO_ODDS"
        assert result.value_bet.active is False

    def test_unknown_fighter_returns_empty_result(self, engine):
        """Context build failure → returns empty IntelligenceResult, never raises."""
        orch = IntelligenceOrchestrator(engine)
        result = orch.compute("Ghost Fighter", "Another Ghost", (0.5, 0.5))

        assert isinstance(result, IntelligenceResult)
        assert result.chaos is None
        assert result.badges == []

    def test_badges_empty_when_all_modules_fail(self, engine):
        """No modules → badge_engine gets all-None → empty badges list."""
        with engine.begin() as conn:
            _seed_fighter(conn, "FE")
            _seed_fighter(conn, "FF")

        orch = IntelligenceOrchestrator(engine)
        result = orch.compute("FE", "FF", (0.55, 0.45))

        assert result.badges == []
