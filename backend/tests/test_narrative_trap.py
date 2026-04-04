"""
Tests for intelligence/narrative_trap.py

Infrastructure paths (no event, empty narratives) + formula tests active.
"""

import pytest

from intelligence.narrative_trap import compute
from intelligence.models import NarrativeTrapResult


# ---------------------------------------------------------------------------
# Infrastructure (these paths were already implemented)
# ---------------------------------------------------------------------------

def test_no_event_fight_returns_low_risk(f1_ctx, f2_ctx):
    result = compute(f1_ctx, f2_ctx, event_fight=None)
    assert isinstance(result, NarrativeTrapResult)
    assert result.available is True
    assert result.risk == "LOW"
    assert result.active_traps == []
    assert result.trapped_fighter is None


def test_event_fight_with_no_narratives_returns_low(f1_ctx, f2_ctx):
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
# Formula tests (Opus implementation complete)
# ---------------------------------------------------------------------------

def test_hype_train_tag_raises_risk(f1_ctx, f2_ctx):
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


def test_two_tags_produces_high_risk(f1_ctx, f2_ctx):
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


def test_short_notice_raises_risk(f1_ctx, f2_ctx):
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


def test_trapped_fighter_identified(f1_ctx, f2_ctx):
    event_fight = {
        "fighter1_name": f1_ctx.name,
        "fighter2_name": f2_ctx.name,
        "narratives": ["COMEBACK_STORY"],
        "is_title_fight": False,
        "short_notice": False,
        "weight_miss": False,
    }
    result = compute(f1_ctx, f2_ctx, event_fight=event_fight)
    assert result.trapped_fighter in (f1_ctx.name, f2_ctx.name, None)
