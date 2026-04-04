"""
Tests for intelligence/nightmare_matchup.py

Infrastructure (style derivation from classify_style): runs now
Formula tests: skipped until Opus implements the nightmare detection.
"""

import pytest

from intelligence.nightmare_matchup import compute
from intelligence.models import NightmareResult


def test_compute_raises_not_implemented_until_opus(f1_ctx, f2_ctx):
    with pytest.raises(NotImplementedError):
        compute(f1_ctx, f2_ctx)


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_returns_nightmare_result(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx)
    assert isinstance(result, NightmareResult)
    assert result.available is True


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_style_labels_always_populated(f1_ctx, f2_ctx):
    """
    style_f1 and style_f2 must always be populated (derived on-the-fly
    from classify_style even when fighters.style is NULL in DB).
    """
    result = compute(f1_ctx, f2_ctx)
    assert result.style_f1 in ("STRIKER", "WRESTLER", "GRAPPLER", "BRAWLER", "COUNTER")
    assert result.style_f2 in ("STRIKER", "WRESTLER", "GRAPPLER", "BRAWLER", "COUNTER")


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_striker_vs_grappler_is_nightmare_for_striker(f1_ctx, f2_ctx):
    """
    f1=STRIKER (slpm=5.8, td_def=0.72), f2=GRAPPLER (td_avg=4.2, sub_avg=2.1).
    The striker faces their nightmare matchup (takedowns + submissions).
    is_nightmare should be True, nightmare_fighter should be f1.
    """
    result = compute(f1_ctx, f2_ctx)
    if result.style_f1 == "STRIKER" and result.style_f2 == "GRAPPLER":
        assert result.is_nightmare is True
        assert result.nightmare_fighter == f1_ctx.name
        assert result.severity in ("MILD", "SEVERE")


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_same_style_is_not_nightmare(dec_ctx_f1, dec_ctx_f2):
    """Two COUNTER fighters facing each other — not a nightmare matchup."""
    result = compute(dec_ctx_f1, dec_ctx_f2)
    if result.style_f1 == result.style_f2:
        assert result.is_nightmare is False
        assert result.severity == "NONE"


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_matchup_label_set_when_nightmare(f1_ctx, f2_ctx):
    """When is_nightmare=True, matchup_label must be a non-None string."""
    result = compute(f1_ctx, f2_ctx)
    if result.is_nightmare:
        assert result.matchup_label is not None
        assert len(result.matchup_label) > 0


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_no_nightmare_has_none_matchup_label(dec_ctx_f1, dec_ctx_f2):
    """When severity=NONE, matchup_label should be None."""
    result = compute(dec_ctx_f1, dec_ctx_f2)
    if result.severity == "NONE":
        assert result.matchup_label is None


@pytest.mark.skip(reason="nightmare_matchup formula: implement in Opus session")
def test_zero_fight_fighter_returns_none_severity(zero_fight_ctx, f1_ctx):
    """
    A fighter with no fight history should not be labelled SEVERE nightmare
    (insufficient data to confirm historical pattern).
    """
    result = compute(zero_fight_ctx, f1_ctx)
    assert result.severity in ("NONE", "MILD")
