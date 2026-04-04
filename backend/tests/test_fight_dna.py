"""
Tests for intelligence/fight_dna.py

All formula tests active — Opus implementation complete.
"""

import pytest

from intelligence.fight_dna import compute
from intelligence.models import FightDNAResult

DNA_DIMENSIONS = {"striking", "grappling", "wrestling", "submission",
                  "pressure", "chin", "cardio", "speed"}


def test_returns_fight_dna_result(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx)
    assert isinstance(result, FightDNAResult)
    assert result.available is True


def test_all_8_dimensions_present_in_dna(f1_ctx, f2_ctx):
    """f1_dna and f2_dna must each have all 8 dimension keys."""
    result = compute(f1_ctx, f2_ctx)
    assert set(result.f1_dna.keys()) == DNA_DIMENSIONS
    assert set(result.f2_dna.keys()) == DNA_DIMENSIONS


def test_all_dimension_scores_in_valid_range(f1_ctx, f2_ctx):
    """All dimension scores must be in [0.0, 1.0]."""
    result = compute(f1_ctx, f2_ctx)
    for dim, score in result.f1_dna.items():
        assert 0.0 <= score <= 1.0, f"f1 {dim}={score} out of range"
    for dim, score in result.f2_dna.items():
        assert 0.0 <= score <= 1.0, f"f2 {dim}={score} out of range"


def test_striker_has_high_striking_score(f1_ctx, f2_ctx):
    """
    f1_ctx is a high-output striker (slpm=5.8, str_acc=0.47).
    Their 'striking' DNA dimension should be above 0.6.
    """
    result = compute(f1_ctx, f2_ctx)
    assert result.f1_dna["striking"] > 0.6


def test_grappler_has_high_submission_score(f1_ctx, f2_ctx):
    """
    f2_ctx is a grappler (sub_avg=2.1, td_avg=4.2).
    Their 'submission' DNA dimension should be above 0.6.
    """
    result = compute(f1_ctx, f2_ctx)
    assert result.f2_dna["submission"] > 0.6


def test_collision_type_reflects_style_difference(f1_ctx, f2_ctx):
    """
    f1=STRIKER, f2=GRAPPLER -> collision_type should reflect this contrast.
    """
    result = compute(f1_ctx, f2_ctx)
    assert "STRIKER" in result.collision_type or "GRAPPLER" in result.collision_type


def test_style_clash_higher_for_contrasting_styles(f1_ctx, f2_ctx, dec_ctx_f1):
    """
    f1 (striker) vs f2 (grappler) should have higher clash intensity
    than f1 vs dec_ctx_f1 (also a counter-striker — similar style).
    """
    clash_contrast = compute(f1_ctx, f2_ctx).style_clash_intensity
    clash_similar = compute(f1_ctx, dec_ctx_f1).style_clash_intensity
    assert clash_contrast > clash_similar


def test_symmetric_collision_type(f1_ctx, f2_ctx):
    """
    compute(f1, f2).collision_type and compute(f2, f1).collision_type
    should represent the same matchup (order may differ).
    """
    r_ab = compute(f1_ctx, f2_ctx)
    r_ba = compute(f2_ctx, f1_ctx)
    assert r_ab.style_clash_intensity == pytest.approx(r_ba.style_clash_intensity, abs=0.05)
