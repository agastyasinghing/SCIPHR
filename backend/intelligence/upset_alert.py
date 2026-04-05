"""
Upset Alert System — surface fights where the model gives meaningful
probability to the betting underdog.  Display name: Dog Teeth.

Output: UpsetResult with is_alert flag, underdog details, and edge.

PRD §10.8 trigger conditions:
    WITH odds:  underdog model_prob >= 0.45
                AND underdog american_odds >= +150
                AND edge (model - implied) >= 0.08
    NO odds:    model_prob >= 0.45 and model_prob < 0.55
                reason = MODEL_CONFIDENCE_NEAR_EVEN

Badge powered: DOG_WITH_TEETH (orange) — shared with perception_gap.
Dashboard:     Upset Watch feed lists all alerts for the current card.

Data source:
    Reads from ValueBetResult (already computed by orchestrator).
    When value_bet.signal is NO_ODDS, falls back to model-confidence-only logic.

TODO(opus): Implement compute() using PRD §10.8 specification.
    Key formula decisions:
    - Underdog identification: fighter with lower implied_prob (from ValueBetResult)
      or lower model_prob when no odds available.
    - Edge: model_probability_for_underdog - implied_probability_for_underdog
    - Thresholds: model_prob >= 0.45, american_odds >= +150, edge >= 0.08
    - No-odds fallback: 0.45 <= model_prob_loser < 0.55 → MODEL_CONFIDENCE_NEAR_EVEN
    - payout_multiplier: american_odds / 100 + 1 (for positive odds)
"""

from __future__ import annotations

from typing import Optional

from .models import FighterContext, UpsetResult, ValueBetResult


def compute(
    f1_ctx: FighterContext,
    f2_ctx: FighterContext,
    model_probs: tuple[float, float],
    value_bet: Optional[ValueBetResult] = None,
) -> UpsetResult:
    """
    Compute the Upset Alert for this matchup.

    Args:
        f1_ctx:      FighterContext for fighter 1.
        f2_ctx:      FighterContext for fighter 2.
        model_probs: (prob_f1, prob_f2) from XGBoost.
        value_bet:   ValueBetResult from the value_bet module (already computed).
                     Provides implied probabilities and American odds.
                     Pass None or a NO_ODDS result for model-confidence-only mode.

    Returns:
        UpsetResult — always returned, never raises.
    """
    # TODO(opus): Implement using PRD §10.8 logic.
    # See module docstring for full specification.
    raise NotImplementedError(
        "upset_alert.compute() — awaiting Opus implementation (PRD §10.8)"
    )
