"""
Nightmare Matchup Detector — detects stylistic nightmares.

Output: NightmareResult with is_nightmare flag, affected fighter,
style labels, and severity.

Display name: Nightmare Matchup
Badge it powers: (FRAUD_CHECK — amber, when nightmare + overvalued)

Known nightmare patterns (a faces nightmare):
    STRIKER  vs GRAPPLER  → SEVERE   striker gets taken down & submitted
    BRAWLER  vs GRAPPLER  → SEVERE   same pattern, brawler walks in
    STRIKER  vs WRESTLER  → MILD     striker controlled on ground
    BRAWLER  vs WRESTLER  → MILD     brawler controlled on ground
    BRAWLER  vs COUNTER   → MILD     brawler walks onto counters
    GRAPPLER vs WRESTLER  → MILD     grappler can't submit, can't stand
    WRESTLER vs STRIKER   → MILD     wrestler can't close distance

Severity downgraded to MILD/NONE when nightmare fighter has < 3 fights.
"""

from __future__ import annotations

from typing import Optional

from .models import FighterContext, NightmareResult
from . import utils


# (style_a, style_b) → base severity when style_a is the nightmare victim
_NIGHTMARE_PATTERNS: dict[tuple[str, str], str] = {
    ("STRIKER", "GRAPPLER"):  "SEVERE",
    ("BRAWLER", "GRAPPLER"):  "SEVERE",
    ("STRIKER", "WRESTLER"):  "MILD",
    ("BRAWLER", "WRESTLER"):  "MILD",
    ("BRAWLER", "COUNTER"):   "MILD",
    ("GRAPPLER", "WRESTLER"): "MILD",
    ("WRESTLER", "STRIKER"):  "MILD",
}


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> NightmareResult:
    """Detect nightmare matchup patterns for this fight."""
    style_f1 = utils.classify_style(f1_ctx.stats)
    style_f2 = utils.classify_style(f2_ctx.stats)

    # ── Check both orientations ───────────────────────────────────────
    nightmare_ctx: Optional[FighterContext] = None
    severity = "NONE"

    pattern = _NIGHTMARE_PATTERNS.get((style_f1, style_f2))
    if pattern:
        nightmare_ctx = f1_ctx
        severity = pattern
    else:
        pattern = _NIGHTMARE_PATTERNS.get((style_f2, style_f1))
        if pattern:
            nightmare_ctx = f2_ctx
            severity = pattern

    # ── No pattern matched ────────────────────────────────────────────
    if nightmare_ctx is None:
        return NightmareResult(
            available=True,
            is_nightmare=False,
            style_f1=style_f1,
            style_f2=style_f2,
            severity="NONE",
        )

    # ── Data-volume guard: downgrade if nightmare fighter has < 3 fights
    if len(nightmare_ctx.fights) < 3:
        severity = "MILD" if severity == "SEVERE" else "NONE"

    if severity == "NONE":
        return NightmareResult(
            available=True,
            is_nightmare=False,
            style_f1=style_f1,
            style_f2=style_f2,
            severity="NONE",
        )

    matchup_label = f"{style_f1}_VS_{style_f2}"

    return NightmareResult(
        available=True,
        is_nightmare=True,
        nightmare_fighter=nightmare_ctx.name,
        style_f1=style_f1,
        style_f2=style_f2,
        matchup_label=matchup_label,
        severity=severity,
    )
