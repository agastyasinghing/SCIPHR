"""
Nightmare Matchup Detector — detects stylistic nightmares.

Output: NightmareResult with is_nightmare flag, affected fighter,
style labels, and severity.

Display name: Nightmare Matchup
Badge it powers: (FRAUD_CHECK — amber, when nightmare + overvalued)

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the nightmare matchup detection formula.

Context:
    fighters.style is NULL for all fighters in v1 (the Phase 1 migration
    does not populate it).  Style is derived on-the-fly via
    utils.classify_style(stats) at predict time and NOT persisted.

Utility functions:
    classify_style(stats) → "STRIKER" | "WRESTLER" | "GRAPPLER" | "BRAWLER" | "COUNTER"

Inputs:
    f1_ctx.stats / f2_ctx.stats  — for classify_style()
    f1_ctx.fights / f2_ctx.fights — for finishing method breakdown
    f1_ctx.wins / losses          — record context

Known nightmare matchup patterns (Opus to assign severity weights):
    WRESTLER  vs STRIKER    → wrestler's nightmare (striker-killer)
                               especially if striker has high str_def + counter style
    GRAPPLER  vs WRESTLER   → grappler's nightmare (can't submit, can't stand up)
    BRAWLER   vs COUNTER    → brawler's nightmare (walks onto counters)
    STRIKER   vs GRAPPLER   → striker's nightmare (gets taken down, submitted)
    BRAWLER   vs GRAPPLER   → brawler's nightmare (same as striker pattern)

Severity classification (Opus to calibrate thresholds):
    NONE   — no clear stylistic nightmare pattern
    MILD   — pattern exists but fighter has shown ability to overcome it
             (e.g., wrestler with decent takedown defence vs striker)
    SEVERE — clear, historically validated nightmare matchup with no
             stat evidence the fighter has overcome the pattern

Mitigating factors (reduce severity):
    - Nightmare fighter has high td_def (wrestler nightmare mitigated)
    - Nightmare fighter has won via the opponent's dominant method before
    - Record is recent and losses are not by the opponent's primary method

Expected output:
    NightmareResult(
        available=True,
        is_nightmare=True | False,
        nightmare_fighter="Fighter Name" | None,
        style_f1="STRIKER",
        style_f2="WRESTLER",
        matchup_label="STRIKER_VS_WRESTLER" | None,
        severity="NONE" | "MILD" | "SEVERE",
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from .models import FighterContext, NightmareResult
from . import utils


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> NightmareResult:
    """
    Detect nightmare matchup patterns for this fight.

    Args:
        f1_ctx: Pre-loaded context for fighter 1.
        f2_ctx: Pre-loaded context for fighter 2.

    Returns:
        NightmareResult. Style labels always populated (derived on-the-fly).

    TODO(opus): Implement the nightmare detection and severity scoring.
    """
    # Style derivation is on-the-fly (fighters.style stays NULL in v1).
    style_f1 = utils.classify_style(f1_ctx.stats)
    style_f2 = utils.classify_style(f2_ctx.stats)

    # TODO(opus): Use style_f1 and style_f2 to detect nightmare patterns.
    # See module docstring for known patterns and severity calibration.
    raise NotImplementedError(
        "nightmare_matchup formula: implement in Opus session. "
        "See module docstring for nightmare pattern table."
    )
