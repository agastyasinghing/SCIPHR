"""
Cinematic Poster Titles — derive a thematic fight title from intelligence signals.

Output: CinematicTitle with title, subtitle, weight_class_color.

PRD §10.17 specification:
    Every fight gets a cinematic title card derived from its matchup dynamics.
    Priority order: specific fight dynamics first, generic last.

    Title templates (PRD §10.17):
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

    Weight class color map (for display/poster styling):
        Heavyweight, Light Heavyweight → "#b45309"   (gold)
        Middleweight, Welterweight      → "#dc2626"   (red)
        Lightweight, Featherweight      → "#2563eb"   (blue)
        Bantamweight, Flyweight         → "#16a34a"   (green)
        Women's divisions               → "#7c3aed"   (violet)
        default                         → "#6b7280"   (gray)

TODO(opus): Implement generate() using PRD §10.17 template system.
    Key implementation decisions:
    - Signal extraction from IntelligenceResult: derive condition strings
      from chaos.tier, nightmare.severity, false_consensus.is_coinflip,
      badges (look for FRAUD_CHECK, AURA_MERCHANT, ROUND_ONE_DEMON,
      DECISION_PRISONER, SILENT_KILLER), narrative_trap.risk, win_path
    - event_fight context needed for: is_title_fight, narratives (REVENGE_FIGHT,
      REMATCH tags), short_notice
    - VETERAN_VS_PROSPECT: approximate via fight count disparity
      (> 15 fight difference between the two fighters)
    - Subtitle: "{fighter1} vs {fighter2} · {weight_class}" + key signal
    - Priority: walk the template list top-to-bottom, return first match
    - Default fallback: CinematicTitle(title="The Matchup", ...)
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


def _weight_class_color(weight_class: str) -> str:
    return _WEIGHT_CLASS_COLORS.get(weight_class, "#6b7280")


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
    # TODO(opus): Implement using PRD §10.17 template system.
    # See module docstring for full specification and template list.
    raise NotImplementedError(
        "cinematic_title.generate() — awaiting Opus implementation (PRD §10.17)"
    )
