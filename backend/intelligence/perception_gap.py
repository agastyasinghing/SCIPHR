"""
Perception Gap Engine — where is public opinion most wrong vs. the model?

Output: PerceptionGapResult with gap scores, labels, and which fighter
is over/undervalued by public perception.

Display name: Perception Gap
Badges it powers: FALSE_FAVORITE (red), PUBLIC_TAX (gold), DOG_WITH_TEETH (orange)
Also used by: false_consensus.compute()

Aura score heuristic (proxy for public perceived strength):
    Component        Weight  Signal
    career_volume    0.20    more fights = more exposure
    finish_rate      0.25    finishers get more clips/attention
    recency          0.20    fights in last ~18 months
    win_streak       0.20    current streak inflates perception
    win_rate         0.15    overall record

    perceived_prob = aura_f1 / (aura_f1 + aura_f2)
    gap_f1 = model_prob_f1 - perceived_prob_f1
"""

from __future__ import annotations

from .models import FighterContext, PerceptionGapResult
from . import utils


# Thresholds for gap classification
_MODERATE_THRESHOLD = 0.10
_STRONG_THRESHOLD = 0.20


def _aura_score(ctx: FighterContext) -> float:
    """
    Heuristic 'public perceived strength' score (0-1).
    Higher = more public attention / hype.
    """
    stats = ctx.stats
    fights = ctx.fights

    # Component 1: career volume (0-0.20)
    volume = min(len(fights) / 30.0, 1.0) * 0.20

    # Component 2: finish rate (0-0.25)
    fr = utils.finish_rate(fights, ctx.name)
    finish_component = fr * 0.25

    # Component 3: recency — fights in roughly last 18 months (0-0.20)
    recent_count = sum(1 for f in fights if (f.get("date") or "") >= "2022-07-01")
    recency = min(recent_count / 4.0, 1.0) * 0.20

    # Component 4: win streak (0-0.20)
    streak = utils.win_streak(fights, ctx.name)
    streak_component = min(max(0, streak) / 8.0, 1.0) * 0.20

    # Component 5: win rate (0-0.15)
    total = ctx.wins + ctx.losses + ctx.draws
    win_rate = ctx.wins / total if total > 0 else 0.0
    wr_component = win_rate * 0.15

    aura = volume + finish_component + recency + streak_component + wr_component
    return min(1.0, max(0.0, aura))


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    model_probs: tuple[float, float],
) -> PerceptionGapResult:
    """Compute the Perception Gap for this matchup."""
    prob_f1, prob_f2 = model_probs

    aura_f1 = _aura_score(f1_ctx)
    aura_f2 = _aura_score(f2_ctx)

    # Convert auras to perceived probabilities via normalisation
    aura_sum = aura_f1 + aura_f2
    if aura_sum > 0:
        perceived_f1 = aura_f1 / aura_sum
        perceived_f2 = aura_f2 / aura_sum
    else:
        perceived_f1 = 0.5
        perceived_f2 = 0.5

    gap_f1 = max(-1.0, min(1.0, prob_f1 - perceived_f1))
    gap_f2 = max(-1.0, min(1.0, prob_f2 - perceived_f2))

    # Classification based on the largest absolute gap
    abs_gap = max(abs(gap_f1), abs(gap_f2))
    if abs_gap >= _STRONG_THRESHOLD:
        label = "STRONG"
    elif abs_gap >= _MODERATE_THRESHOLD:
        label = "MODERATE"
    else:
        label = "NONE"

    # Identify over/undervalued fighters
    overvalued = None
    undervalued = None

    if gap_f1 < -_MODERATE_THRESHOLD:
        overvalued = f1_ctx.name          # model rates f1 LOWER than public
    elif gap_f2 < -_MODERATE_THRESHOLD:
        overvalued = f2_ctx.name

    if gap_f1 > _MODERATE_THRESHOLD:
        undervalued = f1_ctx.name         # model rates f1 HIGHER than public
    elif gap_f2 > _MODERATE_THRESHOLD:
        undervalued = f2_ctx.name

    return PerceptionGapResult(
        available=True,
        gap_f1=round(gap_f1, 4),
        gap_f2=round(gap_f2, 4),
        label=label,
        overvalued_fighter=overvalued,
        undervalued_fighter=undervalued,
        aura_score_f1=round(aura_f1, 4),
        aura_score_f2=round(aura_f2, 4),
    )
