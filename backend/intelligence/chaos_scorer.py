"""
Chaos Scorer — how unpredictable is this fight?

Output: ChaosResult with score 0–100, label, and driver list.

Display name: Chaos Score
Badge it powers: CHAOS_CERTIFIED (yellow)
Also contributes to: Card Temperature (Dashboard), false_consensus

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the chaos scoring formula.

Inputs available in FighterContext:
    f1_ctx.fights / f2_ctx.fights  — full career fight history
    f1_ctx.stats / f2_ctx.stats    — profile stats (slpm, str_acc, td_avg, etc.)
    f1_ctx.wins / losses            — record context

Utility functions available (intelligence/utils.py):
    finish_rate(fights, name)  — proportion of fights ending in finish
    win_streak(fights, name)   — current win/loss streak
    classify_style(stats)      — STRIKER | WRESTLER | GRAPPLER | BRAWLER | COUNTER

Key signals Opus should consider (not exhaustive — Opus decides weights):
    1. finish_rate(f1) + finish_rate(f2)
       High bilateral finish rate = more chaos potential.

    2. Style clash intensity
       Striker vs Wrestler = higher chaos than Striker vs Striker.
       Use classify_style() for both fighters.

    3. Chin issues / KO vulnerability proxy
       High str_acc opponent + low str_def = KO risk.
       Can proxy as: (avg_slpm_opponent / str_def_fighter) if data allows.

    4. Weight class finish rate
       HW/LHW finish much more than FLY/STRAW — add weight_class multiplier.

    5. Record volatility
       A fighter with alternating win/loss pattern signals inconsistency.
       Can detect from fights list: count direction changes in winner sequence.

    6. Win streak direction
       Loss streak + strong opponent = chaos spike (desperation factor).
       Win streak on favourite = slight chaos dampener.

Expected output shape (Opus fills the formula):
    ChaosResult(
        available=True,
        score=float in [0, 100],
        label="LOW" | "MODERATE" | "HIGH" | "EXTREME",
        drivers=["high_finish_rate", "style_clash", ...],  # reasons that fired
        confidence=float in [0, 1],  # lower for fighters with < 5 fights
    )

Label thresholds Opus should validate against OQ-12 (historical upset rates):
    0–30  → LOW
    30–55 → MODERATE
    55–75 → HIGH
    75+   → EXTREME

Validation target (OQ-12 acceptance criterion):
    After formula is implemented, run scripts/validate_chaos_weights.py.
    HIGH/EXTREME fights should show historically higher upset rates than
    LOW/MODERATE fights in the fights table.  See TODOS.md TODO-05.
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from .models import ChaosResult, FighterContext


def compute(f1_ctx: FighterContext, f2_ctx: FighterContext) -> ChaosResult:
    """
    Compute the Chaos Score for this fight.

    Args:
        f1_ctx: Pre-loaded context for fighter 1 (from orchestrator).
        f2_ctx: Pre-loaded context for fighter 2 (from orchestrator).

    Returns:
        ChaosResult with score, label, drivers, and confidence.

    TODO(opus): Implement this formula using the signal guide above.
    """
    raise NotImplementedError(
        "chaos_scorer formula: implement in Opus session. "
        "See module docstring for signal guide and validation target."
    )
