"""
Badge Assignment Engine — reads all intelligence module outputs and
assigns SCIPHR badges for the fighters in this matchup.

Badges are assigned PER FIGHTER (each Badge has a .fighter field).
badge_engine is called last in the orchestrator pipeline because it
depends on all other modules' outputs.

All module result inputs may be None (if _safe_compute caught an error).
badge_engine must handle every combination gracefully — missing a module
input means skipping the badges that required it.

Badge vocabulary (from CLAUDE.md — use these names exactly):
    FRAUD_CHECK       amber   — fighter is overvalued + faces nightmare matchup
    DOG_WITH_TEETH    orange  — underdog is undervalued by public
    FALSE_FAVORITE    red     — fighter is overvalued by public
    DECISION_PRISONER gray    — fighter's only win path is decisions
    ROUND_ONE_DEMON   red     — very high first-round finish rate
    NARRATIVE_HOSTAGE purple  — fight has HIGH narrative risk for this fighter
    CHAOS_CERTIFIED   yellow  — fight chaos score is HIGH or EXTREME
    SILENT_KILLER     teal    — dominant grappler flying under public radar
    PUBLIC_TAX        gold    — public paying a premium for name recognition
    AURA_MERCHANT     violet  — fighter sustained by narrative/aura more than stats
    CASUAL_MIRAGE     pink    — high casual recognition, declining statistical output

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the badge assignment logic.

For each badge, Opus must define:
    1. Which module results are required (and what to do if None)
    2. The threshold condition that fires the badge
    3. Which fighter the badge is assigned to (f1, f2, or both)
    4. A concise reason string explaining why it fired

Suggested badge-to-signal mapping (Opus to refine):
    CHAOS_CERTIFIED   → chaos.score >= threshold (e.g. 65)
    FALSE_FAVORITE    → gap.overvalued_fighter is not None
    DOG_WITH_TEETH    → gap.undervalued_fighter is not None + win_path.available
    NARRATIVE_HOSTAGE → narrative.risk == "HIGH"
    FRAUD_CHECK       → gap.overvalued_fighter + nightmare.is_nightmare (same fighter)
    SILENT_KILLER     → win_path paths dominated by GROUND_AND_POUND/SUBMISSION
                        + perception_gap shows fighter is undervalued
    DECISION_PRISONER → all win_path.f1_paths are DECISION_* variants
    ROUND_ONE_DEMON   → EARLY_KO path is ranked #1 in win_path.f1_paths
    PUBLIC_TAX        → aura_score >> model_prob (fighter costs more in odds
                        than their model-estimated quality justifies)
    AURA_MERCHANT     → high aura_score + declining recent record (losses or
                        late stoppages)
    CASUAL_MIRAGE     → high aura + low actual stats (slpm < median but
                        high name recognition)

BADGE_META in models.py has label + color for each key — use it:
    from .models import BADGE_META
    Badge(key=k, label=BADGE_META[k]["label"], color=BADGE_META[k]["color"],
          reason=reason, fighter=fighter_name)
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import Optional

from .models import (
    BADGE_META,
    Badge,
    ChaosResult,
    FalseConsensusResult,
    FightDNAResult,
    NarrativeTrapResult,
    NightmareResult,
    PerceptionGapResult,
    ValueBetResult,
    WinPathResult,
)


def compute(
    chaos: Optional[ChaosResult] = None,
    gap: Optional[PerceptionGapResult] = None,
    narrative: Optional[NarrativeTrapResult] = None,
    value: Optional[ValueBetResult] = None,
    dna: Optional[FightDNAResult] = None,
    consensus: Optional[FalseConsensusResult] = None,
    nightmare: Optional[NightmareResult] = None,
    win: Optional[WinPathResult] = None,
) -> list[Badge]:
    """
    Assign SCIPHR badges based on all available intelligence module outputs.

    Any input may be None (module failed or not yet implemented).
    When a required input is None, the badge(s) that depend on it are skipped.

    Args:
        chaos:     ChaosResult from chaos_scorer.
        gap:       PerceptionGapResult from perception_gap.
        narrative: NarrativeTrapResult from narrative_trap.
        value:     ValueBetResult from value_bet.
        dna:       FightDNAResult from fight_dna.
        consensus: FalseConsensusResult from false_consensus.
        nightmare: NightmareResult from nightmare_matchup.
        win:       WinPathResult from win_path.

    Returns:
        list[Badge] — may be empty if all inputs are None or no thresholds
        fire for this matchup.
    """
    badges: list[Badge] = []

    # ── Early return: no actionable signals present ───────────────────────
    # Check whether any module produced data that could actually fire a badge.
    # "Available" modules with empty/default values (narrative risk=LOW,
    # value_bet NO_ODDS/inactive) carry no badge-worthy signals.
    # This gate prevents the stub from raising NotImplementedError when
    # there is genuinely nothing to badge.
    def _has_actionable_data() -> bool:
        if chaos is not None and chaos.available:
            return True
        if gap is not None and gap.available:
            return True
        if narrative is not None and narrative.risk != "LOW":
            return True
        if value is not None and value.active:
            return True
        if dna is not None and dna.available:
            return True
        if consensus is not None and consensus.available:
            return True
        if nightmare is not None and nightmare.available:
            return True
        if win is not None and win.available:
            return True
        return False

    if not _has_actionable_data():
        return badges

    # TODO(opus): Implement badge assignment logic.
    #
    # For each badge:
    #   1. Check if required module inputs are not None and available
    #   2. Evaluate threshold condition
    #   3. Create Badge using BADGE_META for label/color:
    #      Badge(
    #          key="CHAOS_CERTIFIED",
    #          label=BADGE_META["CHAOS_CERTIFIED"]["label"],
    #          color=BADGE_META["CHAOS_CERTIFIED"]["color"],
    #          reason="Both fighters have 75%+ finish rate and contrasting styles.",
    #          fighter="<fighter_name>",
    #      )
    #   4. Append to badges list
    #
    # See module docstring for badge-to-signal mapping guide.
    raise NotImplementedError(
        "badge_engine formula: implement in Opus session. "
        "See module docstring for badge-to-signal mapping."
    )
