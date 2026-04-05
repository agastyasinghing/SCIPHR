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

Edge reconstruction: ValueBetResult stores implied_probability; american odds
are reconstructed from that via the standard identities
    american = 100 * (1 - p) / p          when p < 0.5   (underdog → positive)
    american = -100 * p / (1 - p)         when p >= 0.5  (favorite → negative)
At p = 0.40 the reconstructed american is exactly +150, which is the PRD
threshold for the UNDERDOG_EDGE branch.
"""

from __future__ import annotations

from typing import Optional

from .models import FighterContext, UpsetResult, ValueBetResult


def _implied_to_american(implied: float) -> Optional[int]:
    """Reconstruct American moneyline odds from an implied probability."""
    if implied is None or implied <= 0.0 or implied >= 1.0:
        return None
    if implied < 0.5:
        return int(round(100.0 * (1.0 - implied) / implied))
    if implied == 0.5:
        return 100
    return -int(round(100.0 * implied / (1.0 - implied)))


def _payout_multiplier(american: Optional[int]) -> Optional[float]:
    """Return per $1 bet (american / 100 + 1 for positive odds)."""
    if american is None:
        return None
    if american > 0:
        return round(american / 100.0 + 1.0, 4)
    if american < 0:
        return round(100.0 / abs(american) + 1.0, 4)
    return 2.0


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
    prob_f1, prob_f2 = float(model_probs[0]), float(model_probs[1])

    # ── No-odds fallback: model confidence only ──────────────────────
    no_odds = (
        value_bet is None
        or value_bet.signal == "NO_ODDS"
        or value_bet.implied_prob_f1 is None
        or value_bet.implied_prob_f2 is None
    )

    if no_odds:
        # Underdog by model = the fighter with the lower probability
        if prob_f1 <= prob_f2:
            dog_name, dog_prob = f1_ctx.name, prob_f1
        else:
            dog_name, dog_prob = f2_ctx.name, prob_f2

        # PRD §10.8 no-odds trigger: 0.45 <= model_prob < 0.55
        is_alert = 0.45 <= dog_prob < 0.55
        return UpsetResult(
            is_alert=is_alert,
            underdog_name=dog_name if is_alert else None,
            model_probability=round(dog_prob, 4) if is_alert else None,
            reason="MODEL_CONFIDENCE_NEAR_EVEN" if is_alert else None,
        )

    # ── With odds: use ValueBetResult implied probabilities ──────────
    implied_f1 = float(value_bet.implied_prob_f1)
    implied_f2 = float(value_bet.implied_prob_f2)

    # Underdog = fighter with lower implied probability
    if implied_f1 <= implied_f2:
        dog_name = f1_ctx.name
        dog_model_prob = prob_f1
        dog_implied = implied_f1
    else:
        dog_name = f2_ctx.name
        dog_model_prob = prob_f2
        dog_implied = implied_f2

    american = _implied_to_american(dog_implied)
    payout = _payout_multiplier(american)
    edge = dog_model_prob - dog_implied

    # PRD §10.8 trigger: model >= 0.45 AND american >= +150 AND edge >= 0.08
    is_alert = (
        dog_model_prob >= 0.45
        and american is not None
        and american >= 150
        and edge >= 0.08
    )

    return UpsetResult(
        is_alert=is_alert,
        underdog_name=dog_name,
        model_probability=round(dog_model_prob, 4),
        implied_probability=round(dog_implied, 4),
        edge=round(edge, 4),
        american_odds=american,
        payout_multiplier=payout,
        reason="UNDERDOG_EDGE" if is_alert else None,
    )
