"""
Tests for intelligence/badge_engine.py

Infrastructure + all-None path: run now (fully implemented)
Badge assignment logic: skipped until Opus implements the formula.

[22] badge_engine with all-None inputs → empty badge list (testable now)
[27] badge_engine skips badge that needs unavailable module (testable now)
"""

import pytest

from intelligence.badge_engine import compute
from intelligence.models import (
    Badge,
    ChaosResult,
    NarrativeTrapResult,
    PerceptionGapResult,
    ValueBetResult,
)


# ---------------------------------------------------------------------------
# All-None / empty paths (fully implemented — no Opus needed)
# ---------------------------------------------------------------------------

def test_all_none_inputs_returns_empty_list():
    """
    [22] When all module results are None, badge_engine returns [] immediately.
    This path is fully implemented.
    """
    result = compute(
        chaos=None, gap=None, narrative=None, value=None,
        dna=None, consensus=None, nightmare=None, win=None,
    )
    assert isinstance(result, list)
    assert result == []


def test_no_arguments_returns_empty_list():
    """Calling compute() with defaults (all None) returns []."""
    result = compute()
    assert result == []


def test_only_value_bet_no_odds_and_rest_none_returns_empty():
    """
    value_bet=ValueBetResult(NO_ODDS) with everything else None.
    NO_ODDS signal means no line crack badge should fire.
    (All others still None → empty list.)
    """
    value = ValueBetResult(signal="NO_ODDS", active=False)
    result = compute(value=value)
    # value_bet alone with NO_ODDS + all other None → empty
    assert result == []


# ---------------------------------------------------------------------------
# Badge format validation (runs after Opus implements, tests badge structure)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_chaos_certified_badge_fires_above_threshold():
    """
    When chaos.score >= 65 (HIGH), CHAOS_CERTIFIED badge should be assigned.

    Badge must:
      - have key='CHAOS_CERTIFIED'
      - have label='Chaos Certified'
      - have color='yellow'
      - have a non-empty reason string
      - have fighter set to a valid fighter name
    """
    chaos = ChaosResult(score=75.0, label="EXTREME", drivers=["high_finish_rate"])
    result = compute(chaos=chaos)

    chaos_badge = next((b for b in result if b.key == "CHAOS_CERTIFIED"), None)
    assert chaos_badge is not None
    assert chaos_badge.label == "Chaos Certified"
    assert chaos_badge.color == "yellow"
    assert len(chaos_badge.reason) > 0
    assert chaos_badge.fighter is not None


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_chaos_certified_does_not_fire_below_threshold():
    """CHAOS_CERTIFIED should NOT fire for LOW chaos score."""
    chaos = ChaosResult(score=25.0, label="LOW", drivers=[])
    result = compute(chaos=chaos)
    assert not any(b.key == "CHAOS_CERTIFIED" for b in result)


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_narrative_hostage_fires_for_high_risk(f1_ctx):
    """
    NARRATIVE_HOSTAGE badge fires when narrative.risk == 'HIGH'.
    """
    narrative = NarrativeTrapResult(
        risk="HIGH",
        active_traps=["HYPE_TRAIN", "REVENGE_FIGHT"],
        trapped_fighter="F1",
    )
    result = compute(narrative=narrative)
    assert any(b.key == "NARRATIVE_HOSTAGE" for b in result)


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_narrative_hostage_does_not_fire_for_low_risk():
    """NARRATIVE_HOSTAGE should NOT fire when narrative risk is LOW."""
    narrative = NarrativeTrapResult(risk="LOW", active_traps=[], trapped_fighter=None)
    result = compute(narrative=narrative)
    assert not any(b.key == "NARRATIVE_HOSTAGE" for b in result)


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_all_badges_have_valid_keys():
    """Every badge returned must have a key in BADGE_META."""
    from intelligence.models import BADGE_META
    chaos = ChaosResult(score=80.0, label="EXTREME", drivers=["high_finish_rate"])
    narrative = NarrativeTrapResult(
        risk="HIGH", active_traps=["HYPE_TRAIN"], trapped_fighter="F1"
    )
    result = compute(chaos=chaos, narrative=narrative)
    for badge in result:
        assert badge.key in BADGE_META, f"Unknown badge key: {badge.key}"


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_badge_label_and_color_match_badge_meta():
    """Badge label and color must match BADGE_META exactly (CLAUDE.md vocabulary)."""
    from intelligence.models import BADGE_META
    chaos = ChaosResult(score=80.0, label="EXTREME", drivers=["x"])
    result = compute(chaos=chaos)
    for badge in result:
        expected = BADGE_META[badge.key]
        assert badge.label == expected["label"], (
            f"Badge {badge.key}: label {badge.label!r} != {expected['label']!r}"
        )
        assert badge.color == expected["color"], (
            f"Badge {badge.key}: color {badge.color!r} != {expected['color']!r}"
        )


@pytest.mark.skip(reason="badge formula: implement in Opus session")
def test_false_favorite_badge_fires_for_overvalued_fighter():
    """FALSE_FAVORITE fires when gap.overvalued_fighter is not None."""
    gap = PerceptionGapResult(
        gap_f1=-0.25,
        gap_f2=0.25,
        label="STRONG",
        overvalued_fighter="F1",
        undervalued_fighter="F2",
        aura_score_f1=0.85,
        aura_score_f2=0.40,
    )
    result = compute(gap=gap)
    assert any(b.key == "FALSE_FAVORITE" for b in result)
