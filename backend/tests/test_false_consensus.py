"""
Tests for intelligence/false_consensus.py

Skipped until Opus implements the formula.
"""

import pytest

from intelligence.false_consensus import compute
from intelligence.models import ChaosResult, FalseConsensusResult


def test_compute_raises_not_implemented_until_opus(f1_ctx, f2_ctx):
    with pytest.raises(NotImplementedError):
        compute(f1_ctx, f2_ctx, chaos=None, model_probs=(0.55, 0.45))


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_returns_false_consensus_result(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, chaos=None, model_probs=(0.55, 0.45))
    assert isinstance(result, FalseConsensusResult)
    assert result.available is True


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_near_50_50_with_high_chaos_is_coinflip(f1_ctx, f2_ctx):
    """
    model_probs=(0.52, 0.48) — essentially a coinflip.
    chaos.score=80 — EXTREME chaos.
    → is_coinflip should be True.
    """
    chaos = ChaosResult(score=80.0, label="EXTREME", drivers=["x"])
    result = compute(f1_ctx, f2_ctx, chaos=chaos, model_probs=(0.52, 0.48))
    assert result.is_coinflip is True
    assert result.label == "INVISIBLE_COINFLIP"


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_decisive_model_is_not_coinflip(f1_ctx, f2_ctx):
    """
    model_probs=(0.75, 0.25) — decisive favourite.
    Even with chaos present, should NOT be an invisible coinflip.
    """
    chaos = ChaosResult(score=60.0, label="HIGH", drivers=["x"])
    result = compute(f1_ctx, f2_ctx, chaos=chaos, model_probs=(0.75, 0.25))
    assert result.is_coinflip is False
    assert result.label == "NONE"


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_actual_gap_correct(f1_ctx, f2_ctx):
    """actual_gap = abs(prob_f1 - prob_f2)."""
    result = compute(f1_ctx, f2_ctx, chaos=None, model_probs=(0.60, 0.40))
    assert result.actual_gap == pytest.approx(0.20, abs=0.01)


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_actual_gap_in_valid_range(f1_ctx, f2_ctx):
    """actual_gap must be in [0.0, 1.0]."""
    result = compute(f1_ctx, f2_ctx, chaos=None, model_probs=(0.65, 0.35))
    assert 0.0 <= result.actual_gap <= 1.0


@pytest.mark.skip(reason="false_consensus formula: implement in Opus session")
def test_works_without_chaos_input(f1_ctx, f2_ctx):
    """false_consensus should run even if chaos_scorer failed (chaos=None)."""
    result = compute(f1_ctx, f2_ctx, chaos=None, model_probs=(0.53, 0.47))
    assert isinstance(result, FalseConsensusResult)
    assert result.available is True
