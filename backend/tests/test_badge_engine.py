"""
Tests for intelligence/badge_engine.py

All-None / empty paths + badge assignment logic — all active.
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
# All-None / empty paths
# ---------------------------------------------------------------------------

def test_all_none_inputs_returns_empty_list():
    result = compute(
        chaos=None, gap=None, narrative=None, value=None,
        dna=None, consensus=None, nightmare=None, win=None,
    )
    assert isinstance(result, list)
    assert result == []


def test_no_arguments_returns_empty_list():
    result = compute()
    assert result == []


def test_only_value_bet_no_odds_and_rest_none_returns_empty():
    value = ValueBetResult(signal="NO_ODDS", active=False)
    result = compute(value=value)
    assert result == []


# ---------------------------------------------------------------------------
# Badge assignment logic
# ---------------------------------------------------------------------------

def test_chaos_certified_badge_fires_above_threshold():
    chaos = ChaosResult(score=75.0, tier="EXTREME", drivers=["high_finish_rate"])
    result = compute(chaos=chaos)

    chaos_badge = next((b for b in result if b.key == "CHAOS_CERTIFIED"), None)
    assert chaos_badge is not None
    assert chaos_badge.label == "Chaos Certified"
    assert chaos_badge.color == "yellow"
    assert len(chaos_badge.reason) > 0
    assert chaos_badge.fighter is not None


def test_chaos_certified_does_not_fire_below_threshold():
    chaos = ChaosResult(score=25.0, tier="LOW", drivers=[])
    result = compute(chaos=chaos)
    assert not any(b.key == "CHAOS_CERTIFIED" for b in result)


def test_narrative_hostage_fires_for_high_risk(f1_ctx):
    narrative = NarrativeTrapResult(
        risk="HIGH",
        active_traps=["HYPE_TRAIN", "REVENGE_FIGHT"],
        trapped_fighter="F1",
    )
    result = compute(narrative=narrative)
    assert any(b.key == "NARRATIVE_HOSTAGE" for b in result)


def test_narrative_hostage_does_not_fire_for_low_risk():
    narrative = NarrativeTrapResult(risk="LOW", active_traps=[], trapped_fighter=None)
    result = compute(narrative=narrative)
    assert not any(b.key == "NARRATIVE_HOSTAGE" for b in result)


def test_all_badges_have_valid_keys():
    from intelligence.models import BADGE_META
    chaos = ChaosResult(score=80.0, tier="EXTREME", drivers=["high_finish_rate"])
    narrative = NarrativeTrapResult(
        risk="HIGH", active_traps=["HYPE_TRAIN"], trapped_fighter="F1"
    )
    result = compute(chaos=chaos, narrative=narrative)
    for badge in result:
        assert badge.key in BADGE_META, f"Unknown badge key: {badge.key}"


def test_badge_label_and_color_match_badge_meta():
    from intelligence.models import BADGE_META
    chaos = ChaosResult(score=80.0, tier="EXTREME", drivers=["x"])
    result = compute(chaos=chaos)
    for badge in result:
        expected = BADGE_META[badge.key]
        assert badge.label == expected["label"], (
            f"Badge {badge.key}: label {badge.label!r} != {expected['label']!r}"
        )
        assert badge.color == expected["color"], (
            f"Badge {badge.key}: color {badge.color!r} != {expected['color']!r}"
        )


def test_false_favorite_badge_fires_for_overvalued_fighter():
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
