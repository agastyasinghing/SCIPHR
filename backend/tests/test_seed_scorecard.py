"""
Tests for backend/scripts/seed_scorecard.py

Covers:
  [1]  seed() inserts a row into predictions_log with correct fields
  [2]  seed() is idempotent — running twice does not insert duplicate rows
  [3]  seed() sets was_correct=True when predicted_winner matches actual_winner
  [4]  seed() sets was_correct=False when prediction is wrong
  [5]  seed() skips fights where predictor returns None (fighter not in DB)
  [6]  seed() respects after_date — does NOT seed fights before the cutoff
  [7]  seed(dry_run=True) does not write any rows

Setup:
  Uses the in-memory SQLite engine from conftest.py.
  predictor is mocked — tests are pure logic, no model file needed.
"""

import sys
import os
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.seed_scorecard import seed


# ── Helpers ───────────────────────────────────────────────────────────────────

def _insert_fight(engine, r_name, b_name, fight_date, winner):
    """Insert a test fight row into the fights table."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO fights (r_name, b_name, date, winner, method, weight_class)
                VALUES (:r, :b, :d, :w, 'KO', 'Lightweight')
            """),
            {"r": r_name, "b": b_name, "d": str(fight_date), "w": winner},
        )


def _count_predictions(engine):
    with engine.connect() as conn:
        return conn.execute(text("SELECT COUNT(*) FROM predictions_log")).scalar()


def _make_mock_predictor(winner="Fighter A", confidence=0.72):
    m = MagicMock()
    m.predict_fight.return_value = {
        "fighter1": "Fighter A",
        "fighter2": "Fighter B",
        "winner": winner,
        "confidence": confidence,
        "prob_fighter1": 0.72,
        "prob_fighter2": 0.28,
    }
    return m


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSeedScorecard:

    def test_inserts_row_with_correct_fields(self, engine):
        """[1] seed() inserts a predictions_log row with winner, confidence, actual_winner."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 8, 1), "Fighter A")
        mock_pred = _make_mock_predictor(winner="Fighter A")

        inserted = seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        assert inserted == 1
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT winner, confidence, actual_winner, was_correct FROM predictions_log LIMIT 1")
            ).fetchone()
        assert row.winner == "Fighter A"
        assert abs(row.confidence - 0.72) < 0.001
        assert row.actual_winner == "Fighter A"
        assert row.was_correct == 1  # SQLite returns 1 for True

    def test_idempotent_second_run_skips_duplicate(self, engine):
        """[2] Running seed() twice does not insert duplicate rows."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 8, 1), "Fighter A")
        mock_pred = _make_mock_predictor()

        seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)
        seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        assert _count_predictions(engine) == 1

    def test_was_correct_true_when_prediction_matches(self, engine):
        """[3] was_correct=True when predicted_winner == actual_winner."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 8, 2), "Fighter A")
        mock_pred = _make_mock_predictor(winner="Fighter A")

        seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        with engine.connect() as conn:
            row = conn.execute(text("SELECT was_correct FROM predictions_log")).fetchone()
        assert row.was_correct == 1

    def test_was_correct_false_when_prediction_wrong(self, engine):
        """[4] was_correct=False when predicted_winner != actual_winner."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 8, 3), "Fighter B")
        mock_pred = _make_mock_predictor(winner="Fighter A")  # wrong prediction

        seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        with engine.connect() as conn:
            row = conn.execute(text("SELECT was_correct FROM predictions_log")).fetchone()
        assert row.was_correct == 0

    def test_skips_fight_when_predictor_returns_none(self, engine):
        """[5] seed() skips and does not insert when predictor returns None."""
        _insert_fight(engine, "Unknown Fighter X", "Unknown Fighter Y", date(2025, 8, 4), "Unknown Fighter X")
        mock_pred = MagicMock()
        mock_pred.predict_fight.return_value = None

        inserted = seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        assert inserted == 0
        assert _count_predictions(engine) == 0

    def test_respects_after_date_cutoff(self, engine):
        """[6] Fights before after_date are not seeded."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 6, 1), "Fighter A")  # before cutoff
        _insert_fight(engine, "Fighter A", "Fighter C", date(2025, 8, 1), "Fighter A")  # after cutoff
        mock_pred = _make_mock_predictor()

        inserted = seed(engine, after_date=date(2025, 7, 1), _predictor=mock_pred)

        assert inserted == 1  # only the post-cutoff fight
        assert _count_predictions(engine) == 1

    def test_dry_run_does_not_write_rows(self, engine, capsys):
        """[7] dry_run=True prints rows but inserts nothing."""
        _insert_fight(engine, "Fighter A", "Fighter B", date(2025, 8, 5), "Fighter A")
        mock_pred = _make_mock_predictor()

        inserted = seed(engine, after_date=date(2025, 7, 1), dry_run=True, _predictor=mock_pred)

        # dry_run returns count of rows that *would* be inserted
        assert inserted == 1
        # Nothing actually written to DB
        assert _count_predictions(engine) == 0
        # Dry-run output goes to stdout
        captured = capsys.readouterr()
        assert "DRY RUN" in captured.out
