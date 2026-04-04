"""
Perception Gap Engine — where is public opinion most wrong vs. the model?

Output: PerceptionGapResult with gap scores, labels, and which fighter
is over/undervalued by public perception.

Display name: Perception Gap
Badges it powers: FALSE_FAVORITE (red), PUBLIC_TAX (gold), DOG_WITH_TEETH (orange)
Also used by: false_consensus.compute()

─────────────────────────────────────────────────────────────────────
TODO(opus): Implement the perception gap formula.

Context (from STATUS.md Decisions Log):
    "Perception Gap v1: heuristic from dataset proxies"
    Live sentiment data is deferred to v2. v1 uses fighter stats as proxies
    for public perception. The model probability IS the ground truth.

    perception_gap = model_prob_f1 - perceived_prob_f1
    positive = model rates fighter HIGHER than the public heuristic implies
    negative = model rates fighter LOWER (public overvalues them)

Inputs available:
    f1_ctx.stats / f2_ctx.stats  — profile columns
    f1_ctx.fights / f2_ctx.fights — career history
    model_probs                   — (prob_f1, prob_f2) from XGBoost

Utility functions:
    finish_rate(fights, name)  — proportion of fights ending in finish
    win_streak(fights, name)   — current win/loss streak
    classify_style(stats)      — fighting style

Aura score heuristic (Opus decides exact formula):
    "Aura" = proxy for how much hype/public attention a fighter generates.
    Components to consider (not exhaustive):
      1. Career volume: total fights (more fights = more public exposure)
      2. Finish rate: finishers get more attention/clips than decision fighters
      3. Recency: fights in last 18 months weighted higher
      4. Win streak: current streak inflates perception
      5. Weight class multiplier: HW/LHW fights get more mainstream coverage

    aura_score should be normalised 0.0–1.0 relative to the dataset.

    Then: perceived_prob = softmax(aura_f1, aura_f2)[0]
          gap_f1 = model_prob_f1 - perceived_prob_f1

Overvalued/undervalued labels:
    If gap_f1 < -threshold → f1 is overvalued by public (FALSE_FAVORITE)
    If gap_f1 > +threshold → f1 is undervalued (DOG_WITH_TEETH, PUBLIC_TAX)
    Threshold for STRONG label vs MODERATE: Opus to decide via dataset analysis.

Open Question OQ-02:
    "Perception Gap v1 heuristic — honest enough for launch?"
    Opus should assess this before finalising weights.

Expected output:
    PerceptionGapResult(
        available=True,
        gap_f1=float in [-1.0, 1.0],
        gap_f2=float in [-1.0, 1.0],
        label="NONE" | "MODERATE" | "STRONG",
        overvalued_fighter=name_or_None,
        undervalued_fighter=name_or_None,
        aura_score_f1=float in [0.0, 1.0],
        aura_score_f2=float in [0.0, 1.0],
    )
─────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from .models import FighterContext, PerceptionGapResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    model_probs: tuple[float, float],
) -> PerceptionGapResult:
    """
    Compute the Perception Gap for this matchup.

    Args:
        f1_ctx:      Pre-loaded context for fighter 1.
        f2_ctx:      Pre-loaded context for fighter 2.
        model_probs: (prob_f1, prob_f2) from XGBoost prediction.

    Returns:
        PerceptionGapResult with gap, aura scores, and overvalued/undervalued
        fighter identifications.

    TODO(opus): Implement this formula using the signal guide above.
    """
    raise NotImplementedError(
        "perception_gap formula: implement in Opus session. "
        "See module docstring for aura heuristic guide and OQ-02 note."
    )
