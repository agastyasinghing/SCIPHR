"""
Tests for intelligence/narrative_trap.py

Infrastructure + partially-implemented paths: run now
  - no event_fight → LOW risk (fully implemented)
  - event_fight with empty narratives → LOW risk (fully implemented)
Formula tests (tag scoring): skipped until Opus implements.
"""

import pytest

from intelligence.narrative_trap import compute
from intelligence.models import NarrativeTrapResult


# ---------------------------------------------------------------------------
# Infrastructure (runs now — these paths are fully implemented)
# ---------------------------------------------------------------------------

def test_no_event_fight_returns_low_risk(f1_ctx, f2_ctx):
    """
    Ad-hoc /predict with no associated event fight → always LOW risk.
    This path is fully implemented (no Opus needed).
    """
    result = compute(f1_ctx, f2_ctx, event_fight=None)
    assert isinstance(result, NarrativeTrapResult)
    assert result.available is True
    assert result.risk == "LOW"
    assert result.active_traps == []
    assert result.trapped_fighter is None


def test_event_fight_with_no_narratives_returns_low(f1_ctx, f2_ctx):
    """
    Event fight with empty / None narratives → LOW risk.
    Fully implemented path.
    """
    event_fight = {
        "fighter1_name": "F1",
        "fighter2_name": "F2",
        "narratives": [],
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
        "notes": None,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.risk == "LOW"


def test_event_fight_with_null_narratives_returns_low(f1_ctx, f2_ctx):
    """narratives=None should be treated same as empty list → LOW."""
    event_fight = {
        "fighter1_name": "F1",
        "fighter2_name": "F2",
        "narratives": None,
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.risk == "LOW"


# ---------------------------------------------------------------------------
# Formula tests (skipped until Opus implements tag scoring)
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="narrative_trap formula: implement in Opus session")
def test_hype_train_tag_raises_risk(f1_ctx, f2_ctx):
    """
    HYPE_TRAIN narrative tag should raise risk above LOW.
    Expected: MODERATE or HIGH.
    """
    event_fight = {
        "fighter1_name": "F1",
        "fighter2_name": "F2",
        "narratives": ["HYPE_TRAIN"],
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.risk in ("MODERATE", "HIGH")
    assert "HYPE_TRAIN" in result.active_traps


@pytest.mark.skip(reason="narrative_trap formula: implement in Opus session")
def test_two_tags_produces_high_risk(f1_ctx, f2_ctx):
    """Two narrative tags should produce HIGH risk."""
    event_fight = {
        "fighter1_name": "F1",
        "fighter2_name": "F2",
        "narratives": ["HYPE_TRAIN", "REVENGE_FIGHT"],
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.risk == "HIGH"


@pytest.mark.skip(reason="narrative_trap formula: implement in Opus session")
def test_short_notice_raises_risk(f1_ctx, f2_ctx):
    """short_notice=True should raise risk even with no narrative tags."""
    event_fight = {
        "fighter1_name": "F1",
        "fighter2_name": "F2",
        "narratives": [],
        "is_title_fight": False,
        "short_notice": True,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.risk in ("MODERATE", "HIGH")


@pytest.mark.skip(reason="narrative_trap formula: implement in Opus session")
def test_trapped_fighter_identified(f1_ctx, f2_ctx):
    """
    When HYPE_TRAIN or COMEBACK_STORY tag is present, trapped_fighter
    should be set to the fighter the narrative is built around.
    """
    event_fight = {
        "fighter1_name": f1_ctx.name,
        "fighter2_name": f2_ctx.name,
        "narratives": ["COMEBACK_STORY"],
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    # trapped_fighter should be one of the two fighter names
    assert result.trapped_fighter in (f1_ctx.name, f2_ctx.name, None)
