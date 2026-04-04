"""
Tests for intelligence/chaos_scorer.py

All formula tests active — Opus implementation complete.
"""

import pytest

from intelligence.chaos_scorer import compute
from intelligence.models import ChaosResult


def test_high_finish_fighters_score_above_65(high_finish_ctx_f1, high_finish_ctx_f2):
    """
    Two fighters with 100% career finish rate (all fights ended in finish)
    should produce a chaos score >= 65 (HIGH or EXTREME).
    """
    result = compute(high_finish_ctx_f1, high_finish_ctx_f2)
    assert isinstance(result, ChaosResult)
    assert result.available is True
    assert result.score >= 65.0
    assert result.label in ("HIGH", "EXTREME")
    assert len(result.drivers) > 0


def test_decision_specialists_score_below_40(dec_ctx_f1, dec_ctx_f2):
    """
    Two fighters with 0% finish rate (all decisions) should produce
    a chaos score <= 40 (LOW or MODERATE).
    """
    result = compute(dec_ctx_f1, dec_ctx_f2)
    assert isinstance(result, ChaosResult)
    assert result.score <= 40.0
    assert result.label in ("LOW", "MODERATE")


def test_score_is_symmetric(f1_ctx, f2_ctx):
    """
    compute(f1, f2) and compute(f2, f1) should return the same score.
    Chaos is a property of the matchup, not fighter order.
    """
    result_ab = compute(f1_ctx, f2_ctx)
    result_ba = compute(f2_ctx, f1_ctx)
    assert result_ab.score == pytest.approx(result_ba.score, abs=1.0)


def test_new_fighter_returns_low_confidence(zero_fight_ctx, f1_ctx):
    """
    A fighter with zero fight history should produce low confidence
    in the chaos result (data is insufficient to score reliably).
    """
    result = compute(zero_fight_ctx, f1_ctx)
    assert result.confidence < 0.5


def test_drivers_list_not_empty_for_high_score(high_finish_ctx_f1, high_finish_ctx_f2):
    """
    A HIGH or EXTREME chaos score must have at least one driver string
    to explain why the score is high (used in frontend tooltips).
    """
    result = compute(high_finish_ctx_f1, high_finish_ctx_f2)
    if result.label in ("HIGH", "EXTREME"):
        assert len(result.drivers) >= 1


def test_score_within_valid_range(f1_ctx, f2_ctx):
    """Score must always be in [0, 100]."""
    result = compute(f1_ctx, f2_ctx)
    assert 0.0 <= result.score <= 100.0


def test_label_matches_score_bucket(f1_ctx, f2_ctx):
    """
    Label must correspond to score bucket:
        0-30  -> LOW
        30-55 -> MODERATE
        55-75 -> HIGH
        75+   -> EXTREME
    """
    result = compute(f1_ctx, f2_ctx)
    score = result.score
    if score < 30:
        assert result.label == "LOW"
    elif score < 55:
        assert result.label == "MODERATE"
    elif score < 75:
        assert result.label == "HIGH"
    else:
        assert result.label == "EXTREME"
