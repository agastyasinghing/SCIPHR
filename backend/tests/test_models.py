"""
Tests for intelligence/models.py

Covers:
  [1] FighterContext validates required fields
  [2] IntelligenceResult accepts None for all optional modules
  [3] Badge model validates key is a valid BadgeKey (Literal-enforced)
  [4] Field validators catch out-of-range numeric values
"""

import pytest
from pydantic import ValidationError

from intelligence.models import (
    Badge,
    ChaosResult,
    FalseConsensusResult,
    FightDNAResult,
    FighterContext,
    IntelligenceResult,
    NarrativeTrapResult,
    NightmareResult,
    PerceptionGapResult,
    ValueBetResult,
    WinPathResult,
)


# ---------------------------------------------------------------------------
# FighterContext
# ---------------------------------------------------------------------------

class TestFighterContext:
    def test_valid_construction(self, striker_stats):
        ctx = FighterContext(
            name="Test Fighter",
            stats=striker_stats,
            fights=[],
            wins=10,
            losses=2,
            draws=0,
        )
        assert ctx.name == "Test Fighter"
        assert ctx.wins == 10

    def test_name_required(self, striker_stats):
        with pytest.raises(ValidationError):
            FighterContext(stats=striker_stats, fights=[], wins=0, losses=0, draws=0)

    def test_stats_defaults_to_empty_dict_not_required(self):
        # stats is a dict — must be provided but can be empty
        ctx = FighterContext(name="X", stats={}, fights=[], wins=0, losses=0, draws=0)
        assert ctx.stats == {}

    def test_fights_defaults(self):
        ctx = FighterContext(name="X", stats={}, fights=[], wins=0, losses=0, draws=0)
        assert ctx.fights == []

    def test_is_frozen(self, striker_stats):
        ctx = FighterContext(
            name="X", stats=striker_stats, fights=[], wins=0, losses=0, draws=0
        )
        with pytest.raises(Exception):
            ctx.name = "Y"  # frozen model should raise on mutation


# ---------------------------------------------------------------------------
# IntelligenceResult — all optionals accept None
# ---------------------------------------------------------------------------

class TestIntelligenceResult:
    def test_all_none_modules_valid(self):
        result = IntelligenceResult()
        assert result.chaos is None
        assert result.perception_gap is None
        assert result.narrative_trap is None
        assert result.fight_dna is None
        assert result.false_consensus is None
        assert result.nightmare is None
        assert result.win_path is None

    def test_value_bet_defaults_to_no_odds(self):
        result = IntelligenceResult()
        assert result.value_bet.signal == "NO_ODDS"
        assert result.value_bet.active is False

    def test_badges_defaults_to_empty_list(self):
        result = IntelligenceResult()
        assert result.badges == []

    def test_accepts_full_intelligence_result(self):
        result = IntelligenceResult(
            chaos=ChaosResult(score=72.0, label="HIGH"),
            value_bet=ValueBetResult(signal="NO_ODDS"),
            badges=[],
        )
        assert result.chaos.score == 72.0


# ---------------------------------------------------------------------------
# Badge — key is Literal-validated
# ---------------------------------------------------------------------------

class TestBadge:
    def test_valid_badge_key(self):
        badge = Badge(
            key="CHAOS_CERTIFIED",
            label="Chaos Certified",
            color="yellow",
            reason="Both fighters have high finish rates.",
            fighter="F1",
        )
        assert badge.key == "CHAOS_CERTIFIED"

    def test_invalid_badge_key_rejected(self):
        with pytest.raises(ValidationError):
            Badge(
                key="MADE_UP_BADGE",
                label="Whatever",
                color="red",
                reason="test",
                fighter="F1",
            )

    @pytest.mark.parametrize("key", [
        "FRAUD_CHECK", "DOG_WITH_TEETH", "FALSE_FAVORITE", "DECISION_PRISONER",
        "ROUND_ONE_DEMON", "NARRATIVE_HOSTAGE", "CHAOS_CERTIFIED",
        "SILENT_KILLER", "PUBLIC_TAX", "AURA_MERCHANT", "CASUAL_MIRAGE",
    ])
    def test_all_valid_badge_keys_accepted(self, key):
        badge = Badge(key=key, label="Test", color="red", reason="r", fighter="F1")
        assert badge.key == key


# ---------------------------------------------------------------------------
# Field validators — out-of-range values rejected
# ---------------------------------------------------------------------------

class TestFieldValidators:
    def test_chaos_score_above_100_rejected(self):
        with pytest.raises(ValidationError):
            ChaosResult(score=150.0, label="HIGH")

    def test_chaos_score_below_0_rejected(self):
        with pytest.raises(ValidationError):
            ChaosResult(score=-5.0, label="LOW")

    def test_chaos_confidence_above_1_rejected(self):
        with pytest.raises(ValidationError):
            ChaosResult(score=50.0, label="MODERATE", confidence=1.5)

    def test_value_bet_edge_pct_out_of_range(self):
        with pytest.raises(ValidationError):
            ValueBetResult(signal="EDGE_DETECTED", edge_pct=2.0)

    def test_value_bet_kelly_above_half(self):
        with pytest.raises(ValidationError):
            ValueBetResult(signal="STRONG_EDGE", kelly_fraction=0.8)

    def test_perception_gap_out_of_range(self):
        with pytest.raises(ValidationError):
            PerceptionGapResult(gap_f1=1.5, gap_f2=0.0)

    def test_false_consensus_gap_above_1(self):
        with pytest.raises(ValidationError):
            FalseConsensusResult(actual_gap=1.5)

    def test_fight_dna_clash_above_1(self):
        with pytest.raises(ValidationError):
            FightDNAResult(style_clash_intensity=1.1)

    def test_valid_boundary_values_accepted(self):
        # Test exact boundary values are accepted (ge/le not gt/lt)
        r = ChaosResult(score=0.0, label="LOW", confidence=0.0)
        assert r.score == 0.0
        r = ChaosResult(score=100.0, label="EXTREME", confidence=1.0)
        assert r.score == 100.0
