"""
Cinematic Poster Titles — derive a thematic fight title from intelligence signals.

Output: CinematicTitle with title, subtitle, weight_class_color.

PRD §10.17 specification:
    Every fight gets a cinematic title card derived from its matchup dynamics.
    Priority order: specific fight dynamics first, generic last.

    Title templates (PRD §10.17), walked top-to-bottom, first match wins:
        ("HIGH_CHAOS", "BALANCED_DNA")       → "The Chaos Rite"
        ("HIGH_CHAOS", "NIGHTMARE_MATCHUP")  → "Predator Protocol"
        ("LOW_CHAOS", "HIGH_SKILL")          → "Duel of Technicians"
        ("FALSE_CONSENSUS", any)             → "The Invisible Coinflip"
        ("FRAUD_CHECK", any)                 → "The Fraud Check"
        ("LEGACY_SWING", "HIGH")             → "Crown or Collapse"
        ("TITLE_FIGHT", "HIGH_CHAOS")        → "The Chaos Throne"
        ("TITLE_FIGHT", "LOW_CHAOS")         → "The Technical Crown"
        ("UNDERDOG_MODEL", "HIGH_EDGE")      → "The Usurper Test"
        ("VETERAN_VS_PROSPECT", any)         → "Last Stand of the Guard"
        ("REMATCH", "REVENGE")               → "The Reckoning"
        ("DECISION_PRISONERS_BOTH", any)     → "The Attrition War"
        ("ROUND_ONE_DEMONS_BOTH", any)       → "First Blood"
        ("NARRATIVE_SATURATED", any)         → "The Fog of War"
        ("NIGHTMARE_MATCHUP", "SEVERE")      → "Stylistic Execution"
        ("AURA_MERCHANTS_CLASH", any)        → "Merchants of Hype"
        ("SILENT_KILLERS_CLASH", any)        → "Ghost Fight"
        ("DEFAULT", any)                     → "The Matchup"

Signal heuristics:
    HIGH_CHAOS            chaos.tier in {HIGH, EXTREME}
    LOW_CHAOS             chaos.tier == LOW
    BALANCED_DNA          dna.style_clash_intensity < 0.3
    NIGHTMARE_MATCHUP     nightmare.is_nightmare
    HIGH_SKILL            LOW_CHAOS AND combined wins >= 20
    FALSE_CONSENSUS       false_consensus.label == INVISIBLE_COINFLIP
    FRAUD_CHECK           FRAUD_CHECK badge present
    LEGACY_SWING HIGH     avg age >= 33 AND chaos.score >= 50
    TITLE_FIGHT           event_fight.is_title_fight
    UNDERDOG_MODEL HIGH_EDGE  upset_alert.is_alert AND edge >= 0.12
    VETERAN_VS_PROSPECT   |f1.total_fights − f2.total_fights| > 15
    REMATCH + REVENGE     narratives tags contain both
    DECISION_PRISONERS_BOTH  both fighters' win_paths are decision-only
    ROUND_ONE_DEMONS_BOTH    both fighters' top path is EARLY_KO > 0.25
    NARRATIVE_SATURATED   narrative_trap.risk == HIGH
    AURA_MERCHANTS_CLASH  both aura_scores >= 0.65
    SILENT_KILLERS_CLASH  both primary_threats in {GRAPPLING, WRESTLING}
                          AND at least one fighter is undervalued
"""

from __future__ import annotations

from typing import Optional

from .models import (
    CinematicTitle,
    FighterContext,
    IntelligenceResult,
)

# Weight class → CSS hex color token
_WEIGHT_CLASS_COLORS: dict[str, str] = {
    "Heavyweight": "#b45309",
    "Light Heavyweight": "#b45309",
    "Middleweight": "#dc2626",
    "Welterweight": "#dc2626",
    "Lightweight": "#2563eb",
    "Featherweight": "#2563eb",
    "Bantamweight": "#16a34a",
    "Flyweight": "#16a34a",
    "Strawweight": "#16a34a",
    "Women's Featherweight": "#7c3aed",
    "Women's Bantamweight": "#7c3aed",
    "Women's Flyweight": "#7c3aed",
    "Women's Strawweight": "#7c3aed",
}

_DEFAULT_COLOR = "#6b7280"

_DECISION_PATHS = frozenset({"DECISION_VOLUME", "DECISION_COUNTER", "SPLIT_DECISION"})
_GRAPPLING_THREATS = frozenset({"GRAPPLING", "WRESTLING"})


def _weight_class_color(weight_class: str) -> str:
    return _WEIGHT_CLASS_COLORS.get(weight_class, _DEFAULT_COLOR)


def _has_badge(intelligence: IntelligenceResult, key: str) -> bool:
    return any(b.key == key for b in intelligence.badges)


def _all_decision(paths: list[dict]) -> bool:
    """True if every path > 10% probability is a decision variant."""
    if not paths:
        return False
    significant = [p for p in paths if (p.get("probability") or 0) > 0.10]
    return bool(significant) and all(p.get("path") in _DECISION_PATHS for p in significant)


def _is_r1_demon(paths: list[dict]) -> bool:
    if not paths:
        return False
    top = paths[0]
    return top.get("path") == "EARLY_KO" and (top.get("probability") or 0) > 0.25


def generate(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    intelligence: IntelligenceResult,
    weight_class: str = "Unknown",
    event_fight: Optional[dict] = None,
) -> CinematicTitle:
    """
    Derive the cinematic title for this fight from intelligence signals.

    Args:
        f1_ctx:       FighterContext for fighter 1.
        f2_ctx:       FighterContext for fighter 2.
        intelligence: Full IntelligenceResult bundle from the orchestrator.
        weight_class: Fight weight class string (for color and subtitle).
        event_fight:  event_fights row dict — provides is_title_fight and
                      narratives tags (REVENGE_FIGHT, REMATCH etc.).

    Returns:
        CinematicTitle — always returned, never raises.
        Falls back to CinematicTitle(title="The Matchup") if no template matches.
    """
    ef = event_fight or {}
    narratives = set(ef.get("narratives") or [])
    is_title_fight = bool(ef.get("is_title_fight"))

    # ── Extract modules (any may be None) ────────────────────────────
    chaos = intelligence.chaos
    dna = intelligence.fight_dna
    nightmare = intelligence.nightmare
    fc = intelligence.false_consensus
    narrative = intelligence.narrative_trap
    win = intelligence.win_path
    gap = intelligence.perception_gap
    upset = intelligence.upset_alert

    # ── Condition signals ────────────────────────────────────────────
    high_chaos = chaos is not None and chaos.available and chaos.tier in ("HIGH", "EXTREME")
    low_chaos = chaos is not None and chaos.available and chaos.tier == "LOW"
    balanced_dna = dna is not None and dna.available and dna.style_clash_intensity < 0.3
    nightmare_match = nightmare is not None and nightmare.available and nightmare.is_nightmare
    nightmare_severe = nightmare is not None and nightmare.available and nightmare.severity == "SEVERE"
    false_consensus_fired = fc is not None and fc.available and fc.label == "INVISIBLE_COINFLIP"
    fraud_check = _has_badge(intelligence, "FRAUD_CHECK")
    narrative_saturated = narrative is not None and narrative.available and narrative.risk == "HIGH"

    combined_wins = (f1_ctx.wins or 0) + (f2_ctx.wins or 0)
    high_skill = low_chaos and combined_wins >= 20

    avg_age = ((f1_ctx.stats.get("age") or 0) + (f2_ctx.stats.get("age") or 0)) / 2.0
    legacy_swing_high = (
        avg_age >= 33
        and chaos is not None and chaos.available and chaos.score >= 50
    )

    underdog_high_edge = (
        upset is not None
        and upset.is_alert
        and upset.edge is not None
        and upset.edge >= 0.12
    )

    f1_total = (f1_ctx.wins or 0) + (f1_ctx.losses or 0) + (f1_ctx.draws or 0)
    f2_total = (f2_ctx.wins or 0) + (f2_ctx.losses or 0) + (f2_ctx.draws or 0)
    vet_vs_prospect = abs(f1_total - f2_total) > 15

    rematch_revenge = "REMATCH" in narratives and "REVENGE_FIGHT" in narratives

    decision_prisoners_both = (
        win is not None and win.available
        and _all_decision(win.f1_paths) and _all_decision(win.f2_paths)
    )
    round_one_demons_both = (
        win is not None and win.available
        and _is_r1_demon(win.f1_paths) and _is_r1_demon(win.f2_paths)
    )

    aura_merchants_clash = (
        gap is not None and gap.available
        and gap.aura_score_f1 >= 0.65 and gap.aura_score_f2 >= 0.65
    )
    silent_killers_clash = (
        win is not None and win.available
        and win.f1_primary_threat in _GRAPPLING_THREATS
        and win.f2_primary_threat in _GRAPPLING_THREATS
        and gap is not None and gap.available
        and gap.undervalued_fighter is not None
    )

    # ── Walk templates in PRD §10.17 priority order ──────────────────
    if high_chaos and balanced_dna:
        title = "The Chaos Rite"
    elif high_chaos and nightmare_match:
        title = "Predator Protocol"
    elif low_chaos and high_skill:
        title = "Duel of Technicians"
    elif false_consensus_fired:
        title = "The Invisible Coinflip"
    elif fraud_check:
        title = "The Fraud Check"
    elif legacy_swing_high:
        title = "Crown or Collapse"
    elif is_title_fight and high_chaos:
        title = "The Chaos Throne"
    elif is_title_fight and low_chaos:
        title = "The Technical Crown"
    elif underdog_high_edge:
        title = "The Usurper Test"
    elif vet_vs_prospect:
        title = "Last Stand of the Guard"
    elif rematch_revenge:
        title = "The Reckoning"
    elif decision_prisoners_both:
        title = "The Attrition War"
    elif round_one_demons_both:
        title = "First Blood"
    elif narrative_saturated:
        title = "The Fog of War"
    elif nightmare_severe:
        title = "Stylistic Execution"
    elif aura_merchants_clash:
        title = "Merchants of Hype"
    elif silent_killers_clash:
        title = "Ghost Fight"
    else:
        title = "The Matchup"

    subtitle = f"{f1_ctx.name} vs {f2_ctx.name} · {weight_class}"

    return CinematicTitle(
        title=title,
        subtitle=subtitle,
        weight_class_color=_weight_class_color(weight_class),
    )
