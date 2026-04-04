"""
Win Path Heuristics — how does each fighter win, and what does that
mean for this specific matchup?

Display name: Kill Chain
Used by: badge_engine (DECISION_PRISONER, ROUND_ONE_DEMON, SILENT_KILLER)

Context (from STATUS.md Decisions Log):
    "Win Path: heuristic only (renamed Kill Chain)"
    Model retrain for probabilistic win path is deferred to v3.
    v1 uses fighter stats and fight history as heuristic inputs.

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the Kill Chain heuristic formula.

Inputs available:
    f1_ctx.stats / f2_ctx.stats  — profile columns
    f1_ctx.fights / f2_ctx.fights — career fight history with methods
    model_probs                   — (prob_f1, prob_f2) from XGBoost

Utility functions:
    finish_rate(fights, name)  — overall finish involvement rate
    win_streak(fights, name)   — current streak
    classify_style(stats)      — primary style

Win path labels (Opus assigns probability weights):
    EARLY_KO           — finish in rounds 1-2 via KO/TKO
    GROUND_AND_POUND   — TKO via ground work (high td_avg + finish rate)
    SUBMISSION         — sub_avg > threshold + grappling style
    TAKEDOWN_CONTROL   — high td_avg, low sub_avg (wrestler-dominant path)
    DECISION_VOLUME    — high slpm, wins by decision (striker without finishing)
    DECISION_COUNTER   — counter-style + decisions (str_def-dominant)
    SPLIT_DECISION     — close fights, competitive exchanges

Method for each win path:
    1. Derive primary style from classify_style()
    2. Look at career finish methods from fights list
       (count KO/TKO wins vs Sub wins vs Decision wins)
    3. Weight recent fights more than older fights (recency bonus)
    4. For opponent context: use their str_def, td_def to see which
       of our paths face the most resistance

most_likely_method:
    KO | TKO | SUB | DEC | SPLIT_DEC | UNKNOWN
    Derived from dominant path and style clash.

primary_threat:
    What should the OPPONENT fear most from this fighter?
    Used by frontend to highlight danger zones.
    e.g. "GRAPPLING", "STRIKING", "CLINCH", "CARDIO"

Expected output:
    WinPathResult(
        available=True,
        f1_paths=[
            {"path": "GROUND_AND_POUND", "probability": 0.42},
            {"path": "SUBMISSION", "probability": 0.28},
            {"path": "DECISION_VOLUME", "probability": 0.18},
            {"path": "EARLY_KO", "probability": 0.12},
        ],
        f2_paths=[...],
        most_likely_method="TKO",
        f1_primary_threat="GRAPPLING",
        f2_primary_threat="STRIKING",
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from .models import FighterContext, WinPathResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    model_probs: tuple[float, float],
) -> WinPathResult:
    """
    Compute the Kill Chain (win path heuristics) for both fighters.

    Args:
        f1_ctx:      Pre-loaded context for fighter 1.
        f2_ctx:      Pre-loaded context for fighter 2.
        model_probs: (prob_f1, prob_f2) — used to weight path probabilities.

    Returns:
        WinPathResult with ordered path lists and primary threat labels.

    TODO(opus): Implement the Kill Chain heuristic formula.
    """
    raise NotImplementedError(
        "win_path (Kill Chain) formula: implement in Opus session. "
        "See module docstring for path label guide and weight calibration."
    )
