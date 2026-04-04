"""
Fight DNA Calculator — what kind of fight will this be, dimensionally?

Output: FightDNAResult with 8-dimension profiles for each fighter,
a collision type, and style clash intensity.

Display name: Fight DNA
Used by: badge_engine (DECISION_PRISONER, ROUND_ONE_DEMON logic)
Frontend: Fight DNA visual component (Phase 4)

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the Fight DNA dimension scoring formula.

Eight dimensions (Opus assigns weights from fighter stats):
    STRIKING      — slpm, str_acc, knockdowns proxy
    GRAPPLING     — td_avg, td_acc, td_def
    WRESTLING     — td_avg, td_acc (separate from grappling submission focus)
    SUBMISSION    — sub_avg, td_acc
    PRESSURE      — slpm + td_avg combined (pace/aggression proxy)
    CHIN          — str_def, losses-by-KO proxy from fights list
    CARDIO        — fights that went to later rounds / decision rate
    SPEED         — slpm / str_acc ratio proxy (high output + accuracy = speed)

Each dimension score: 0.0 (weak) → 1.0 (elite), normalised across dataset.

Inputs available:
    f1_ctx.stats / f2_ctx.stats  — profile columns
    f1_ctx.fights / f2_ctx.fights — career history (for chin, cardio proxies)

Utility functions:
    finish_rate(fights, name)  — overall finish involvement
    classify_style(stats)      — primary style label

Collision type logic:
    Derived from both fighters' dominant dimension (highest score).
    Format: "{f1_dominant}_VS_{f2_dominant}"
    e.g. "STRIKER_VS_WRESTLER", "GRAPPLER_VS_GRAPPLER"

Style clash intensity:
    0.0 = mirror match (same dominant dimension)
    1.0 = maximum opposition (e.g. pure striker vs. pure grappler)
    Intermediate values for partial overlaps.

expected output:
    FightDNAResult(
        available=True,
        f1_dna={"striking": 0.82, "grappling": 0.34, ...},  # 8 keys
        f2_dna={"striking": 0.41, "grappling": 0.79, ...},
        collision_type="STRIKER_VS_GRAPPLER",
        style_clash_intensity=0.73,
        primary_dimension="STRIKING",  # most decisive for this matchup
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from .models import FighterContext, FightDNAResult


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> FightDNAResult:
    """
    Compute the Fight DNA profile for both fighters and their collision.

    Args:
        f1_ctx: Pre-loaded context for fighter 1.
        f2_ctx: Pre-loaded context for fighter 2.

    Returns:
        FightDNAResult with dimension scores, collision type, and clash intensity.

    TODO(opus): Implement the 8-dimension scoring formula.
    """
    raise NotImplementedError(
        "fight_dna formula: implement in Opus session. "
        "See module docstring for dimension list and collision type logic."
    )
