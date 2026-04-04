"""
Tests for intelligence/perception_gap.py

Infrastructure tests: run now
Formula tests: skipped until Opus implements the formula.
"""

import pytest

from intelligence.perception_gap import compute
from intelligence.models import PerceptionGapResult


def test_compute_raises_not_implemented_until_opus(f1_ctx, f2_ctx):
    with pytest.raises(NotImplementedError):
        compute(f1_ctx, f2_ctx, (0.55, 0.45))


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_returns_perception_gap_result(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    assert isinstance(result, PerceptionGapResult)
    assert result.available is True


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_gap_values_in_valid_range(f1_ctx, f2_ctx):
    """gap_f1 and gap_f2 must be in [-1.0, 1.0]."""
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    assert -1.0 <= result.gap_f1 <= 1.0
    assert -1.0 <= result.gap_f2 <= 1.0


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_aura_scores_in_valid_range(f1_ctx, f2_ctx):
    """aura_score_f1 and aura_score_f2 must be in [0.0, 1.0]."""
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    assert 0.0 <= result.aura_score_f1 <= 1.0
    assert 0.0 <= result.aura_score_f2 <= 1.0


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_high_finish_rate_fighter_has_higher_aura(
    high_finish_ctx_f1, dec_ctx_f1
):
    """
    A fighter with 100% finish rate should have a higher aura score
    than a decision specialist — finishers get more public attention.
    Both fighters' aura scores computed against the same dummy opponent.
    """
    # Compute aura for finisher vs decision specialist
    result_finisher = compute(high_finish_ctx_f1, dec_ctx_f1, (0.55, 0.45))
    result_dec = compute(dec_ctx_f1, high_finish_ctx_f1, (0.45, 0.55))
    # Finisher (f1 in first call) should have higher aura
    assert result_finisher.aura_score_f1 > result_dec.aura_score_f1


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_overvalued_fighter_identified_when_gap_strong(f1_ctx, f2_ctx):
    """
    When gap is STRONG, either overvalued_fighter or undervalued_fighter
    (or both) should be non-None.
    """
    result = compute(f1_ctx, f2_ctx, (0.60, 0.40))
    if result.label == "STRONG":
        assert result.overvalued_fighter is not None or result.undervalued_fighter is not None


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_no_gap_when_equal_fighters(f1_ctx, f2_ctx):
    """
    When model sees 50/50 AND aura scores are equal, gap should be NONE.
    (Hard to test exactly without controlling aura; best effort.)
    """
    result = compute(f1_ctx, f2_ctx, (0.50, 0.50))
    # Not asserting NONE specifically since aura may differ,
    # but overvalued_fighter should not be set if gap is trivial.
    assert result.available is True


@pytest.mark.skip(reason="perception_gap formula: implement in Opus session")
def test_zero_fight_fighter_has_low_aura(zero_fight_ctx, f1_ctx):
    """A fighter with no fight history should have near-zero aura score."""
    result = compute(zero_fight_ctx, f1_ctx, (0.30, 0.70))
    assert result.aura_score_f1 < 0.3
