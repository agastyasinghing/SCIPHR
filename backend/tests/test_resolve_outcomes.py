"""
Tests for backend/scripts/resolve_outcomes.py

Covers:
  [1]  resolve() updates actual_winner + was_correct=True when prediction was correct
  [2]  resolve() sets was_correct=False when prediction was wrong
  [3]  Matching is order-insensitive (fighter1/fighter2 can be swapped in the result entry)
  [4]  dry_run=True previews without writing any rows
  [5]  No matching rows → logs warning, no crash, no DB changes
  [6]  Winner not in fight entry → skips the entry (no update)
  [7]  Idempotent — running twice with same input produces the same was_correct/actual_winner
  [8]  event_id filter — only updates rows with matching event_id (or NULL event_id)
  [9]  actual_method and actual_round are persisted when provided

Setup:
  Uses the in-memory SQLite engine from conftest.py.
  resolve() is called directly with the test engine — no subprocess needed.
"""

import sys
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from scripts.resolve_outcomes import resolve


# ── Helpers ───────────────────────────────────────────────────────────────────

def _insert_prediction(engine, fighter1, fighter2, winner, event_id=None, fight_id=None):
    """Insert a minimal predictions_log row; returns the inserted row id."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO predictions_log (fighter1, fighter2, winner, confidence, prob_f1, prob_f2, event_id, fight_id)
                VALUES (:f1, :f2, :w, 0.65, 0.65, 0.35, :eid, :fid)
            """),
            {"f1": fighter1, "f2": fighter2, "w": winner, "eid": event_id, "fid": fight_id},
        )
        return conn.execute(text("SELECT last_insert_rowid()")).scalar()


def _fetch_prediction(engine, row_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT actual_winner, was_correct, actual_method, actual_round, resolved_at FROM predictions_log WHERE id = :id"),
            {"id": row_id},
        ).fetchone()
    return row


def _count_resolved(engine):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT COUNT(*) FROM predictions_log WHERE was_correct IS NOT NULL")
        ).scalar()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestResolveOutcomes:

    def test_correct_prediction_sets_was_correct_true(self, engine):
        """[1] Prediction winner matches actual_winner → was_correct=True."""
        row_id = _insert_prediction(engine, "Jon Jones", "Stipe Miocic", "Jon Jones")
        results = [{"fighter1": "Jon Jones", "fighter2": "Stipe Miocic", "actual_winner": "Jon Jones"}]

        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert row.actual_winner == "Jon Jones"
        assert bool(row.was_correct) is True

    def test_wrong_prediction_sets_was_correct_false(self, engine):
        """[2] Prediction winner differs from actual_winner → was_correct=False."""
        row_id = _insert_prediction(engine, "Jon Jones", "Stipe Miocic", "Jon Jones")
        results = [{"fighter1": "Jon Jones", "fighter2": "Stipe Miocic", "actual_winner": "Stipe Miocic"}]

        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert row.actual_winner == "Stipe Miocic"
        assert bool(row.was_correct) is False

    def test_matching_is_order_insensitive(self, engine):
        """[3] fighter1/fighter2 order in result entry does not need to match DB order."""
        row_id = _insert_prediction(engine, "Islam Makhachev", "Charles Oliveira", "Islam Makhachev")
        # Result entry has fighters in reverse order vs DB row
        results = [{"fighter1": "Charles Oliveira", "fighter2": "Islam Makhachev", "actual_winner": "Islam Makhachev"}]

        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert bool(row.was_correct) is True

    def test_dry_run_does_not_write(self, engine):
        """[4] dry_run=True previews without committing any changes."""
        row_id = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A")
        results = [{"fighter1": "Fighter A", "fighter2": "Fighter B", "actual_winner": "Fighter A"}]

        resolve(engine, results, event_id=None, dry_run=True)

        row = _fetch_prediction(engine, row_id)
        assert row.was_correct is None  # unchanged
        assert row.actual_winner is None  # unchanged

    def test_no_matching_rows_does_not_crash(self, engine):
        """[5] Result entry with no matching predictions_log rows → warning, no crash."""
        results = [{"fighter1": "Ghost Fighter", "fighter2": "Nobody", "actual_winner": "Ghost Fighter"}]
        # Should complete without raising
        resolve(engine, results, event_id=None, dry_run=False)
        assert _count_resolved(engine) == 0

    def test_winner_not_in_fight_skips_entry(self, engine):
        """[6] actual_winner not matching either fighter → entry skipped, no DB write."""
        row_id = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A")
        results = [{"fighter1": "Fighter A", "fighter2": "Fighter B", "actual_winner": "Fighter C"}]

        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert row.was_correct is None  # unchanged

    def test_idempotent_same_result_twice(self, engine):
        """[7] Running resolve twice with identical input gives the same was_correct."""
        row_id = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A")
        results = [{"fighter1": "Fighter A", "fighter2": "Fighter B", "actual_winner": "Fighter A"}]

        resolve(engine, results, event_id=None, dry_run=False)
        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert bool(row.was_correct) is True
        assert row.actual_winner == "Fighter A"

    def test_event_id_filter_only_updates_matching_event(self, engine):
        """[8] event_id filter — row with different event_id is NOT updated."""
        row_event_1 = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A", event_id=1)
        row_event_2 = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A", event_id=2)
        results = [{"fighter1": "Fighter A", "fighter2": "Fighter B", "actual_winner": "Fighter B"}]

        resolve(engine, results, event_id=1, dry_run=False)

        row1 = _fetch_prediction(engine, row_event_1)
        row2 = _fetch_prediction(engine, row_event_2)
        assert bool(row1.was_correct) is False  # updated (event_id matches)
        assert row2.was_correct is None          # untouched (event_id=2 ≠ filter 1)

    def test_actual_method_and_round_persisted(self, engine):
        """[9] actual_method and actual_round are written when provided."""
        row_id = _insert_prediction(engine, "Fighter A", "Fighter B", "Fighter A")
        results = [{
            "fighter1": "Fighter A",
            "fighter2": "Fighter B",
            "actual_winner": "Fighter A",
            "actual_method": "KO",
            "actual_round": 1,
        }]

        resolve(engine, results, event_id=None, dry_run=False)

        row = _fetch_prediction(engine, row_id)
        assert row.actual_method == "KO"
        assert row.actual_round == 1
