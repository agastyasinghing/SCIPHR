"""
Tests for intelligence/cinematic_title.py (PRD §10.17).

Verifies:
    - Template priority order (first-match-wins)
    - Signal extraction from IntelligenceResult
    - Weight class color mapping
    - Subtitle format
    - Default fallback
"""

import pytest

from intelligence.cinematic_title import generate, _weight_class_color
from intelligence.models import (
    Badge,
    BADGE_META,
    ChaosResult,
    CinematicTitle,
    FalseConsensusResult,
    FightDNAResult,
    IntelligenceResult,
    NarrativeTrapResult,
    NightmareResult,
    PerceptionGapResult,
    UpsetResult,
    WinPathResult,
)


# ---------------------------------------------------------------------------
# Default fallback
# ---------------------------------------------------------------------------

def test_empty_intelligence_returns_default(f1_ctx, f2_ctx):
    """All signals absent → 'The Matchup'."""
    result = generate(f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Lightweight")
    assert isinstance(result, CinematicTitle)
    assert result.title == "The Matchup"
    assert f1_ctx.name in result.subtitle
    assert f2_ctx.name in result.subtitle
    assert "Lightweight" in result.subtitle
    # Lightweight → blue color
    assert result.weight_class_color == "#2563eb"


def test_unknown_weight_class_uses_default_color(f1_ctx, f2_ctx):
    result = generate(f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Unknown")
    assert result.weight_class_color == "#6b7280"


# ---------------------------------------------------------------------------
# Template priority order
# ---------------------------------------------------------------------------

def test_high_chaos_balanced_dna_wins(f1_ctx, f2_ctx):
    """HIGH_CHAOS + BALANCED_DNA is priority 1 → 'The Chaos Rite'."""
    intel = IntelligenceResult(
        chaos=ChaosResult(score=80.0, tier="EXTREME"),
        fight_dna=FightDNAResult(style_clash_intensity=0.2),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Lightweight")
    assert result.title == "The Chaos Rite"


def test_high_chaos_nightmare_matchup(f1_ctx, f2_ctx):
    """HIGH_CHAOS + NIGHTMARE → 'Predator Protocol' (beats later templates)."""
    intel = IntelligenceResult(
        chaos=ChaosResult(score=70.0, tier="HIGH"),
        fight_dna=FightDNAResult(style_clash_intensity=0.8),  # not balanced
        nightmare=NightmareResult(is_nightmare=True, severity="SEVERE"),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Welterweight")
    assert result.title == "Predator Protocol"


def test_false_consensus_before_title_fight(f1_ctx, f2_ctx):
    """FALSE_CONSENSUS (priority 4) beats TITLE_FIGHT (priority 7)."""
    intel = IntelligenceResult(
        chaos=ChaosResult(score=65.0, tier="HIGH"),
        false_consensus=FalseConsensusResult(
            is_coinflip=True, label="INVISIBLE_COINFLIP", actual_gap=0.05,
        ),
    )
    result = generate(
        f1_ctx, f2_ctx, intel, weight_class="Lightweight",
        event_fight={"is_title_fight": True},
    )
    assert result.title == "The Invisible Coinflip"


def test_fraud_check_badge_wins(f1_ctx, f2_ctx):
    """FRAUD_CHECK badge fires → 'The Fraud Check' (priority 5)."""
    intel = IntelligenceResult(
        badges=[Badge(
            key="FRAUD_CHECK",
            label=BADGE_META["FRAUD_CHECK"]["label"],
            color=BADGE_META["FRAUD_CHECK"]["color"],
            reason="overvalued + nightmare matchup",
            fighter=f1_ctx.name,
        )],
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Middleweight")
    assert result.title == "The Fraud Check"
    # Middleweight → red
    assert result.weight_class_color == "#dc2626"


def test_title_fight_high_chaos(f1_ctx, f2_ctx):
    """TITLE_FIGHT + HIGH_CHAOS (no earlier match) → 'The Chaos Throne'."""
    intel = IntelligenceResult(
        chaos=ChaosResult(score=70.0, tier="HIGH"),
        fight_dna=FightDNAResult(style_clash_intensity=0.7),  # not balanced
        # no nightmare, no false_consensus, no fraud_check
    )
    result = generate(
        f1_ctx, f2_ctx, intel, weight_class="Lightweight",
        event_fight={"is_title_fight": True},
    )
    assert result.title == "The Chaos Throne"


def test_title_fight_low_chaos(f1_ctx, f2_ctx):
    """TITLE_FIGHT + LOW_CHAOS → 'The Technical Crown'.

    Uses zero-win fixture fighters to avoid HIGH_SKILL branch matching first.
    """
    from intelligence.models import FighterContext
    f1_small = FighterContext(name="F1", stats={}, fights=[], wins=5, losses=0, draws=0)
    f2_small = FighterContext(name="F2", stats={}, fights=[], wins=5, losses=0, draws=0)

    intel = IntelligenceResult(chaos=ChaosResult(score=20.0, tier="LOW"))
    result = generate(
        f1_small, f2_small, intel, weight_class="Bantamweight",
        event_fight={"is_title_fight": True},
    )
    assert result.title == "The Technical Crown"


def test_underdog_high_edge_fires(f1_ctx, f2_ctx):
    """upset.is_alert + edge >= 0.12 → 'The Usurper Test'."""
    intel = IntelligenceResult(
        upset_alert=UpsetResult(is_alert=True, edge=0.20, reason="UNDERDOG_EDGE"),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Heavyweight")
    assert result.title == "The Usurper Test"


def test_underdog_alert_low_edge_does_not_fire(f1_ctx, f2_ctx):
    """is_alert=True but edge < 0.12 → does not fire Usurper Test."""
    intel = IntelligenceResult(
        upset_alert=UpsetResult(is_alert=True, edge=0.08, reason="UNDERDOG_EDGE"),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Heavyweight")
    assert result.title == "The Matchup"


def test_veteran_vs_prospect_large_gap(f1_ctx, f2_ctx):
    """|total_fights diff| > 15 → 'Last Stand of the Guard'."""
    from intelligence.models import FighterContext
    veteran = FighterContext(name="Vet", stats={}, fights=[], wins=25, losses=5, draws=0)
    prospect = FighterContext(name="Prospect", stats={}, fights=[], wins=8, losses=0, draws=0)
    result = generate(veteran, prospect, IntelligenceResult(), weight_class="Lightweight")
    assert result.title == "Last Stand of the Guard"


def test_rematch_revenge(f1_ctx, f2_ctx):
    """REMATCH + REVENGE_FIGHT narratives → 'The Reckoning'."""
    result = generate(
        f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Lightweight",
        event_fight={"narratives": ["REMATCH", "REVENGE_FIGHT"]},
    )
    assert result.title == "The Reckoning"


def test_rematch_only_does_not_fire_reckoning(f1_ctx, f2_ctx):
    """REMATCH alone (no REVENGE_FIGHT) → not 'The Reckoning'."""
    result = generate(
        f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Lightweight",
        event_fight={"narratives": ["REMATCH"]},
    )
    assert result.title != "The Reckoning"


def test_narrative_saturated(f1_ctx, f2_ctx):
    """narrative.risk==HIGH → 'The Fog of War'."""
    intel = IntelligenceResult(
        narrative_trap=NarrativeTrapResult(
            risk="HIGH", active_traps=["HYPE_TRAIN", "LEGACY_FIGHT"],
        ),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Lightweight")
    assert result.title == "The Fog of War"


def test_nightmare_severe_alone(f1_ctx, f2_ctx):
    """NIGHTMARE SEVERE with no HIGH_CHAOS → 'Stylistic Execution'."""
    intel = IntelligenceResult(
        chaos=ChaosResult(score=40.0, tier="MIXED"),
        nightmare=NightmareResult(is_nightmare=True, severity="SEVERE"),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Welterweight")
    assert result.title == "Stylistic Execution"


def test_aura_merchants_clash(f1_ctx, f2_ctx):
    """Both aura >= 0.65 → 'Merchants of Hype'."""
    intel = IntelligenceResult(
        perception_gap=PerceptionGapResult(
            aura_score_f1=0.80, aura_score_f2=0.70,
        ),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Lightweight")
    assert result.title == "Merchants of Hype"


def test_decision_prisoners_both(f1_ctx, f2_ctx):
    """Both fighters' win paths are decision-only → 'The Attrition War'."""
    intel = IntelligenceResult(
        win_path=WinPathResult(
            f1_paths=[{"path": "DECISION_VOLUME", "probability": 0.60}],
            f2_paths=[{"path": "DECISION_COUNTER", "probability": 0.55}],
        ),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Featherweight")
    assert result.title == "The Attrition War"


def test_round_one_demons_both(f1_ctx, f2_ctx):
    """Both fighters top path = EARLY_KO > 0.25 → 'First Blood'."""
    intel = IntelligenceResult(
        win_path=WinPathResult(
            f1_paths=[{"path": "EARLY_KO", "probability": 0.40}],
            f2_paths=[{"path": "EARLY_KO", "probability": 0.35}],
        ),
    )
    result = generate(f1_ctx, f2_ctx, intel, weight_class="Heavyweight")
    assert result.title == "First Blood"


# ---------------------------------------------------------------------------
# Subtitle & color
# ---------------------------------------------------------------------------

def test_subtitle_contains_both_names_and_weight_class(f1_ctx, f2_ctx):
    result = generate(f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Welterweight")
    assert f1_ctx.name in result.subtitle
    assert f2_ctx.name in result.subtitle
    assert "Welterweight" in result.subtitle
    assert "vs" in result.subtitle.lower()


def test_weight_class_color_map():
    assert _weight_class_color("Heavyweight") == "#b45309"
    assert _weight_class_color("Light Heavyweight") == "#b45309"
    assert _weight_class_color("Middleweight") == "#dc2626"
    assert _weight_class_color("Welterweight") == "#dc2626"
    assert _weight_class_color("Lightweight") == "#2563eb"
    assert _weight_class_color("Featherweight") == "#2563eb"
    assert _weight_class_color("Bantamweight") == "#16a34a"
    assert _weight_class_color("Women's Bantamweight") == "#7c3aed"
    assert _weight_class_color("Not A Weight Class") == "#6b7280"


def test_result_is_valid_pydantic_model(f1_ctx, f2_ctx):
    result = generate(f1_ctx, f2_ctx, IntelligenceResult(), weight_class="Lightweight")
    rehydrated = CinematicTitle(**result.model_dump())
    assert rehydrated.title == "The Matchup"
    assert rehydrated.weight_class_color == "#2563eb"
